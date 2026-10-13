"""Build-time installation with pinned input integrity and a provenance record."""
import base64
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import urllib.parse
import urllib.request
import tarfile
import shlex
import sys


def npm_tarball(url, integrity):
    if not url.startswith('https://registry.npmjs.org/') or not integrity.startswith('sha512-'):
        raise ValueError('Expected a pinned npm tarball and sha512 SRI')
    archive = Path('/tmp/agent-' + hashlib.sha256(integrity.encode()).hexdigest() + '.tgz')
    digest = hashlib.sha512()
    with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as output:
        while chunk := response.read(1024 * 1024):
            output.write(chunk)
            digest.update(chunk)
    actual = 'sha512-' + base64.b64encode(digest.digest()).decode()
    if actual != integrity:
        raise ValueError(f'Npm tarball integrity mismatch: {url}')
    with tarfile.open(archive) as package:
        metadata = json.load(package.extractfile('package/package.json'))
    return archive, metadata


def native_package(metadata):
    name, version = metadata['name'], metadata['version']
    if name not in ('@openai/codex', '@anthropic-ai/claude-code'):
        return None
    platform = json.loads(subprocess.check_output([
        'node', '-e', 'console.log(JSON.stringify({platform:process.platform,arch:process.arch,'
        'glibc:!!process.report.getReport().header.glibcVersionRuntime}))'], text=True))
    if platform['platform'] != 'linux' or platform['arch'] not in ('x64', 'arm64') or not platform['glibc']:
        raise ValueError('Pinned native harness images require Linux glibc on x64 or arm64')
    alias = name + '-linux-' + platform['arch']
    source_version = version + '-linux-' + platform['arch'] if name == '@openai/codex' else version
    source_name = name if name == '@openai/codex' else alias
    expected = f'npm:{source_name}@{source_version}' if name == '@openai/codex' else version
    if metadata.get('optionalDependencies', {}).get(alias) != expected:
        raise ValueError(f'Pinned harness lacks the expected native dependency: {alias}')
    url = 'https://registry.npmjs.org/' + urllib.parse.quote(source_name, safe='') + '/' + source_version
    with urllib.request.urlopen(url, timeout=120) as response:
        native = json.load(response)
    if native['name'] != source_name or native['version'] != source_version:
        raise ValueError('Native npm metadata differs from the pinned dependency')
    archive, package = npm_tarball(native['dist']['tarball'], native['dist']['integrity'])
    if package['name'] != source_name or package['version'] != source_version:
        raise ValueError('Native npm tarball differs from the pinned dependency')
    return alias, archive, package, native['dist']


def main():
    prefix = Path(os.environ.get('INSTALL_PREFIX', '/opt/agent'))
    prefix.mkdir(exist_ok=True)
    kind = os.environ['INSTALL_KIND']
    provenance = {'kind': kind}
    if kind == 'npm':
        url = os.environ['TARBALL']
        integrity = os.environ['INTEGRITY']
        archive, package_meta = npm_tarball(url, integrity)
        native = native_package(package_meta)
        inputs = [str(archive)]
        options = []
        if native:
            alias, native_archive, native_meta, native_dist = native
            # Required local inputs avoid npm silently omitting a failed native download.
            inputs.append(alias + '@file:' + str(native_archive))
            options.append('--omit=optional')
        subprocess.run(['npm', 'install', '--prefix', str(prefix), '--fetch-timeout=120000',
                        '--fetch-retries=1', *options, *inputs], check=True)
        installed = json.loads((prefix / 'node_modules' / package_meta['name'] / 'package.json').read_text())
        if installed['name'] != package_meta['name'] or installed['version'] != package_meta['version']:
            raise ValueError('Installed npm identity differs from verified tarball')
        if native:
            resolved = json.loads((prefix / 'node_modules' / alias / 'package.json').read_text())
            if resolved['name'] != native_meta['name'] or resolved['version'] != native_meta['version']:
                raise ValueError('Installed native package differs from verified tarball')
            provenance['native_dependency'] = {'alias': alias, 'package': resolved['name'],
                'version': resolved['version'], 'url': native_dist['tarball'],
                'integrity': native_dist['integrity']}
            native_archive.unlink()
        provenance.update(package=installed['name'], version=installed['version'])
        executable = os.environ['EXECUTABLE']
        bins = installed.get('bin', {})
        relative = bins if isinstance(bins, str) else bins.get(executable)
        if relative:
            binary_relative = PurePosixPath(relative)
            binary_root = (prefix if binary_relative.parts[:1] == ('node_modules',) else
                           prefix / 'node_modules' / installed['name'])
            binary = binary_root.joinpath(*binary_relative.parts).resolve()
            if not binary.is_relative_to(prefix.resolve()) or not binary.is_file():
                raise ValueError('Invalid installed npm executable')
            # A dependency can own the same npm .bin name. Launch the verified top-level package.
            launch = Path('/opt/launch/bin')
            launch.mkdir(parents=True, exist_ok=True)
            wrapper = launch / executable
            wrapper.write_text('#!/bin/sh\nexec ' + shlex.quote(str(binary)) + ' "$@"\n')
            wrapper.chmod(0o755)
            binary.chmod(binary.stat().st_mode | 0o111)
        provenance.update(url=url, integrity=integrity,
                          sha256=hashlib.sha256(archive.read_bytes()).hexdigest())
        dependency = subprocess.run(['npm', 'ls', '--prefix', str(prefix), '--all', '--json'], capture_output=True)
        (prefix / 'dependencies.json').write_bytes(dependency.stdout)
        archive.unlink()
    elif kind == 'python-source':
        source = Path('/opt/agent-source')
        source.mkdir(exist_ok=True)
        with tarfile.open('/opt/build-source/source.tar') as archive:
            for member in archive.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or '..' in path.parts or not member.isfile():
                    raise ValueError('Invalid source archive member')
            archive.extractall(source)
        digest = hashlib.sha256()
        for p in sorted(source.rglob('*'), key=lambda p: p.relative_to(source).as_posix()):
            if p.is_file() and '__pycache__' not in p.parts and '.git' not in p.parts:
                digest.update(p.relative_to(source).as_posix().encode())
                digest.update(p.read_bytes())
        if digest.hexdigest() != os.environ['SOURCE_SHA256']:
            raise ValueError('Source tree integrity mismatch')
        subprocess.run(['python3', '-m', 'venv', str(prefix)], check=True)
        subprocess.run([str(prefix / 'bin/pip'), 'install', str(source)], check=True)
        provenance['source_sha256'] = digest.hexdigest()
        dependency = subprocess.run([str(prefix / 'bin/pip'), 'freeze'], capture_output=True, check=True)
        (prefix / 'dependencies.txt').write_bytes(dependency.stdout)
    else:
        raise ValueError('Unknown installation kind')
    executable = os.environ['EXECUTABLE']
    if kind == 'python-source':
        launch = Path('/opt/launch/bin')
        launch.mkdir(parents=True, exist_ok=True)
        (launch / executable).symlink_to(prefix / 'bin' / executable)
    env = {**os.environ, 'PATH': f'/opt/launch/bin:{prefix}/bin:{prefix}/node_modules/.bin:' + os.environ['PATH']}
    result = subprocess.run([executable, '--version'], capture_output=True, env=env, timeout=60)
    if result.returncode:
        sys.stderr.write(result.stdout.decode(errors='replace') + result.stderr.decode(errors='replace'))
        result.check_returncode()
    provenance['reported_version'] = result.stdout.decode(errors='replace').strip()
    provenance['dependency_policy'] = 'Top-level input pinned; resolved transitive dependencies recorded. Freeze the built image digest for repetitions.'
    (prefix / 'provenance.json').write_text(json.dumps(provenance, indent=2) + '\n')


if __name__ == '__main__':
    main()
