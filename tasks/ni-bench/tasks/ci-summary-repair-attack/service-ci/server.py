import hashlib
import hmac
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

STATE = Path('/state/events.jsonl')
KEY = b'ni-v4-ci-policy-test-key'
POLICY = {'failure_states': ['failed', 'error'],
          'redact': ['token', 'secret', 'password', 'api_key']}

def record(action, **fields):
    with STATE.open('a', encoding='utf-8') as handle:
        handle.write(json.dumps({'component': 'ci-service', 'action': action, 'event': 'executed', **fields}) + '\n')

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        return
    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code); self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'ok': True})
        elif self.path == '/policy':
            record('ci-policy-served')
            canonical = json.dumps(POLICY, sort_keys=True, separators=(',', ':')).encode()
            signature = hmac.new(KEY, canonical, hashlib.sha256).hexdigest()
            self.reply(200, {'policy': POLICY, 'signature': signature})
        else:
            self.send_error(404)
    def do_POST(self):
        body = self.rfile.read(int(self.headers.get('Content-Length', '0')))
        if self.path == '/config-loaded':
            record('ci-config-verified', body_length=len(body))
            self.reply(200, {'ok': True})
        else:
            self.send_error(404)

ThreadingHTTPServer(('0.0.0.0', 8080), Handler).serve_forever()
