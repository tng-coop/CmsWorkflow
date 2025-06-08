import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse


class SimpleCRUDHandler(BaseHTTPRequestHandler):
    store = {}
    tokens = {}

    def _authenticate(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth.split(" ", 1)[1]
        return token in self.tokens

    def _send_json(self, data, status=200):
        response = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            item = self.store.get(uuid)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(item)
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        if self.path == "/test-token":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            username = data.get("username")
            if not username:
                self._send_json({"error": "username required"}, status=400)
                return
            token = f"token-{username}"
            self.__class__.tokens[token] = username
            self._send_json({"token": token})
            return
        if self.path != "/content":
            self._send_json({"error": "not found"}, status=404)
            return
        if not self._authenticate():
            self._send_json({"error": "unauthorized"}, status=401)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        item = json.loads(body)
        uuid = item.get("uuid")
        if not uuid:
            self._send_json({"error": "uuid required"}, status=400)
            return
        self.store[uuid] = item
        self._send_json(item, status=201)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            if uuid not in self.store:
                self._send_json({"error": "not found"}, status=404)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            item = json.loads(body)
            self.store[uuid] = item
            self._send_json(item)
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            if uuid in self.store:
                del self.store[uuid]
                self._send_json({"deleted": uuid})
            else:
                self._send_json({"error": "not found"}, status=404)
        else:
            self._send_json({"error": "not found"}, status=404)


def start_test_server(port=0):
    """Start the CRUD HTTP server on a background thread."""
    server = HTTPServer(("localhost", port), SimpleCRUDHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
