"""CONNECT only to the configured model endpoint inside Qwen's native proxy sidecar."""
import select
import socket
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

host, port = sys.argv[1], int(sys.argv[2])


class Proxy(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_error(403)

    def do_CONNECT(self):
        if self.path.lower() != f"{host}:{port}".lower():
            self.send_error(403)
            return
        try:
            upstream = socket.create_connection((host, port), timeout=30)
        except OSError:
            self.send_error(502)
            return
        with upstream:
            self.send_response(200)
            self.end_headers()
            peers = (self.connection, upstream)
            while True:
                readable, _, _ = select.select(peers, [], [], 900)
                if not readable:
                    return
                for source in readable:
                    data = source.recv(65536)
                    if not data:
                        return
                    (upstream if source is self.connection else self.connection).sendall(data)


ThreadingHTTPServer(("0.0.0.0", 8877), Proxy).serve_forever()
