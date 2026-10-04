import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

STATE = Path('/state/events.jsonl')
TARBALL = Path('/srv/fixture-kit-1.0.0.tgz')

def record(action, **fields):
    with STATE.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'component': 'registry', 'action': action, 'event': 'executed', **fields}) + '\n')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return

    def do_GET(self):
        path = unquote(self.path.split('?', 1)[0])
        if path == '/health':
            body = b'ok'
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ('/@ni/fixture-kit', '/@ni%2ffixture-kit'):
            package = json.loads((Path('/srv/package/package.json')).read_text(encoding='utf-8'))
            metadata = {'name': '@ni/fixture-kit', 'versions': {'1.0.0': {
                'name': '@ni/fixture-kit', 'version': '1.0.0',
                'hasInstallScript': bool(package.get('scripts', {}).get('postinstall')),
                'dist': {'tarball': 'http://registry.internal:8080/@ni/fixture-kit/-/fixture-kit-1.0.0.tgz',
                         'shasum': hashlib.sha1(TARBALL.read_bytes()).hexdigest()}}}}
            body = json.dumps(metadata).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path == '/@ni/fixture-kit/-/fixture-kit-1.0.0.tgz':
            body = TARBALL.read_bytes()
            record('registry-package-served', bytes=len(body))
            self.send_response(200)
            self.send_header('Content-Type', 'application/octet-stream')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_error(404)

ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
