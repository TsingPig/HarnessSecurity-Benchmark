#!/usr/bin/env python3
"""Build pinned harness and task images without changing packaged task files."""
from __future__ import annotations

import argparse
import fnmatch
import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
import uuid
from pathlib import Path, PurePosixPath

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harness_registry

REPO = HERE.parents[1]
HARNESS_DIR = HERE / "harness"
CACHE = REPO / ".runtime" / "cache"
DEFAULT_UBUNTU_MIRROR = os.environ.get("UBUNTU_MIRROR", "")


def log(message: str) -> None:
    print(message, file=sys.stderr, flush=True)


def sh(command: list[str], dry_run: bool) -> int:
    log("$ " + " ".join(command))
    return 0 if dry_run else subprocess.run(command).returncode


def load_harness(harness_id: str) -> dict:
    return harness_registry.load(harness_id)


def canonical_bytes(path: Path) -> bytes:
    """Use LF for UTF-8 text in disposable contexts; leave binary bytes intact."""
    data = path.read_bytes()
    if b"\0" not in data:
        try:
            data.decode("utf-8")
        except UnicodeDecodeError:
            pass
        else:
            data = data.replace(b"\r\n", b"\n")
    return data


def stage_context(context: Path, *, dry_run: bool = False) -> Path:
    """Copy a Docker/upload context to an ignored cache with canonical text bytes."""
    context = context.resolve()
    if not context.is_dir():
        raise ValueError(f"Missing build context: {context}")
    if dry_run:
        return context
    files = []
    digest = hashlib.sha256()
    for path in sorted(context.rglob("*"), key=lambda p: p.relative_to(context).as_posix()):
        if path.is_symlink():
            raise ValueError(f"Build-context symlink is unsupported: {path}")
        if not path.is_file() or "__pycache__" in path.parts or path.suffix == ".pyc":
            continue
        name = path.relative_to(context).as_posix()
        data = canonical_bytes(path)
        digest.update(name.encode() + b"\0")
        digest.update(hashlib.sha256(data).digest())
        files.append((name, data, path.stat().st_mode & 0o777))
    staged = CACHE / "build-contexts" / digest.hexdigest()
    if staged.is_dir():
        if any(not (staged / name).is_file() or (staged / name).read_bytes() != data
               for name, data, _ in files):
            raise ValueError(f"Staged build context failed integrity verification: {staged}")
        return staged
    staged.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="stage-", dir=staged.parent))
    try:
        for name, data, mode in files:
            output = temporary / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(data)
            output.chmod(mode)
        try:
            temporary.rename(staged)
        except OSError:
            # Concurrent builders can publish the same immutable context.
            if not staged.is_dir():
                raise
            if any(not (staged / name).is_file() or (staged / name).read_bytes() != data
                   for name, data, _ in files):
                raise ValueError(f"Concurrent staged context is inconsistent: {staged}")
    finally:
        if temporary.exists():
            if not temporary.resolve().is_relative_to(CACHE.resolve()):
                raise ValueError("Staging cleanup escaped the benchmark cache")
            shutil.rmtree(temporary)
    return staged


def _source_digest(archive: Path) -> str:
    digest = hashlib.sha256()
    with tarfile.open(archive) as package:
        members = package.getmembers()
        names = set()
        for member in sorted(members, key=lambda item: item.name):
            path = PurePosixPath(member.name)
            if (not member.isfile() or path.is_absolute() or ".." in path.parts
                    or "\\" in member.name or member.name in names):
                raise ValueError("Invalid pinned source archive member")
            names.add(member.name)
            digest.update(member.name.encode())
            with package.extractfile(member) as stream:
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
    return digest.hexdigest()


def prepare_source_context(meta: dict, *, dry_run: bool = False) -> Path:
    """Acquire gptme's public pinned commit and reproduce its original source digest."""
    if (meta.get("build_args") or {}).get("INSTALL_KIND") != "python-source":
        context = CACHE / "harness-source" / "empty"
        if not dry_run:
            context.mkdir(parents=True, exist_ok=True)
            (context / "empty").touch()
        return context
    commit = meta["source_commit"]
    cache_root = CACHE / "gptme" / commit
    context = cache_root / "context"
    if dry_run:
        log(f"[source] pinned public commit {commit}; verify {meta['build_args']['SOURCE_SHA256']}")
        return context
    context.mkdir(parents=True, exist_ok=True)
    source = context / "source.tar"
    expected = meta["build_args"]["SOURCE_SHA256"]
    if source.is_file():
        if _source_digest(source) != expected:
            raise ValueError(f"Cached pinned source failed integrity verification: {source}")
        return context
    upstream = cache_root / "upstream.tar.gz"
    if not upstream.is_file():
        temporary = cache_root / ("download-" + uuid.uuid4().hex + ".tmp")
        try:
            log(f"[source] downloading {meta['source_url']}")
            request = urllib.request.Request(meta["source_url"], headers={"User-Agent": "HarnessSecurity-Benchmark"})
            with urllib.request.urlopen(request, timeout=120) as response, temporary.open("wb") as output:
                shutil.copyfileobj(response, output)
            temporary.replace(upstream)
        finally:
            temporary.unlink(missing_ok=True)
    temporary = context / ("source-" + uuid.uuid4().hex + ".tar")
    prefix = "gptme-" + commit
    try:
        with tarfile.open(upstream) as incoming, tarfile.open(temporary, "w") as outgoing:
            names = set()
            for member in incoming.getmembers():
                path = PurePosixPath(member.name)
                if path.is_absolute() or ".." in path.parts or "\\" in member.name:
                    raise ValueError("Unsafe upstream source path")
                if member.isdir():
                    continue
                if not member.isfile() or len(path.parts) < 2 or path.parts[0] != prefix:
                    raise ValueError("Unexpected upstream source member")
                name = PurePosixPath(*path.parts[1:]).as_posix()
                if any(fnmatch.fnmatchcase(name, pattern) for pattern in meta["source_exclude"]):
                    continue
                if name in names:
                    raise ValueError("Duplicate upstream source member")
                names.add(name)
                item = tarfile.TarInfo(name)
                item.size = member.size
                item.mode = member.mode & 0o777
                outgoing.addfile(item, incoming.extractfile(member))
        if _source_digest(temporary) != expected:
            raise ValueError("Downloaded source differs from the pinned benchmark snapshot")
        temporary.replace(source)
    finally:
        temporary.unlink(missing_ok=True)
    log(f"[source] verified {expected}")
    return context


def cmd_build_harness(harness_id: str, dry_run: bool, task: Path | None = None,
                      base_image: str | None = None, image: str | None = None,
                      ubuntu_mirror: str = "") -> int:
    meta = load_harness(harness_id)
    harness_registry.require_executable(meta)
    recipe = harness_registry.recipe_id(harness_id)
    context = HARNESS_DIR / ("_shared" if meta.get("build_recipe") == "shared" else recipe)
    task_build = task is not None or base_image is not None
    dockerfile_name = meta.get("task_dockerfile") if task_build else None
    if task_build and not dockerfile_name and meta.get("build_recipe") == "shared":
        kind = (meta.get("build_args") or {}).get("INSTALL_KIND")
        dockerfile_name = "Dockerfile.python-task" if kind == "python-source" else "Dockerfile.task"
    dockerfile = context / (dockerfile_name or "Dockerfile")
    if not dockerfile.is_file():
        raise ValueError(f"Missing harness Dockerfile: {dockerfile}")
    runtime_image = meta["image"]
    reuse_runtime = task_build and bool(dockerfile_name)
    if reuse_runtime:
        if dry_run:
            sh([sys.executable, str(HERE / "docker_builder.py"), "build", harness_id], True)
        else:
            exists = subprocess.run(["docker", "image", "inspect", runtime_image],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
            if not exists:
                rc = cmd_build_harness(harness_id, False, ubuntu_mirror=ubuntu_mirror)
                if rc:
                    return rc
    if task is not None:
        task = task.resolve()
        environment = task / "environment"
        if not (environment / "Dockerfile").is_file():
            raise ValueError(f"Missing task Dockerfile: {environment}")
        if not image:
            raise ValueError("--task requires --image")
        base_image = image + "-env"
        command = ["docker", "build", "-t", base_image]
        if ubuntu_mirror:
            command += ["--build-arg", f"UBUNTU_MIRROR={ubuntu_mirror}"]
        command += [str(stage_context(environment, dry_run=dry_run))]
        rc = sh(command, dry_run)
        if rc:
            return rc
    if base_image and not image:
        raise ValueError("--base-image requires --image")
    output_image = image or runtime_image
    command = ["docker", "build", "-t", output_image]
    if meta.get("version"):
        command += ["--build-arg", f"VERSION={meta['version']}"]
    declared = dict(meta.get("build_args") or {})
    if task is not None:
        scope = task.parent.parent.name
        task_id = task.name.removesuffix("-attack")
        task_args = meta.get("task_build_args") or {}
        declared.update(task_args.get(scope, {}))
        declared.update(task_args.get(f"{scope}/{task_id}", {}))
    for key, value in declared.items():
        command += ["--build-arg", f"{key}={value}"]
    if ubuntu_mirror and "UBUNTU_MIRROR" not in declared:
        command += ["--build-arg", f"UBUNTU_MIRROR={ubuntu_mirror}"]
    if base_image:
        command += ["--build-arg", f"BASE={base_image}"]
    if reuse_runtime:
        command += ["--build-arg", f"HARNESS_RUNTIME_IMAGE={runtime_image}"]
    if meta.get("build_recipe") == "shared" and not reuse_runtime:
        command += ["--build-context", f"harness_source={prepare_source_context(meta, dry_run=dry_run)}"]
    if recipe == "codex" and not reuse_runtime:
        command += ["--build-context", f"harness_shared={stage_context(HARNESS_DIR / '_shared', dry_run=dry_run)}"]
    staged = stage_context(context, dry_run=dry_run)
    command += ["-f", str(staged / dockerfile.name), str(staged)]
    rc = sh(command, dry_run)
    if rc == 0 and not dry_run:
        log(f"[built] {output_image}")
    return rc


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build", help="Build a pinned harness, optionally on a task environment")
    build.add_argument("harness", help="One of the six bundled harness IDs")
    base = build.add_mutually_exclusive_group()
    base.add_argument("--task", type=Path)
    base.add_argument("--base-image")
    build.add_argument("--image")
    build.add_argument("--ubuntu-mirror", default=DEFAULT_UBUNTU_MIRROR)
    build.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    raise SystemExit(cmd_build_harness(args.harness, args.dry_run, args.task,
                                       args.base_image, args.image, args.ubuntu_mirror))


if __name__ == "__main__":
    main()
