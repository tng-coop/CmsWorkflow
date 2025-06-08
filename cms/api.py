import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse

from .types import ContentType
from .workflow import check_required_metadata, request_approval, start_draft


class SimpleCRUDHandler(BaseHTTPRequestHandler):
    """Serve a very small CRUD API for content items.

    The handler validates that the ``type`` field of incoming data matches one
    of the values defined in :class:`cms.types.ContentType`.
    """

    store = {}
    metadata_store = {}
    tokens = {}
    valid_types = {ct.value for ct in ContentType}

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
        if parsed.path == "/content-types":
            self._send_json(sorted(self.valid_types))
            return
        if parsed.path == "/pending-approvals":
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            pending = [
                dict(item, metadata=self.metadata_store.get(uid, {}))
                for uid, item in self.store.items()
                if item.get("state") == "AwaitingApproval"
            ]
            self._send_json(pending)
            return
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            item = self.store.get(uuid)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                metadata = self.metadata_store.get(uuid, {})
                item = dict(item)
                item["metadata"] = metadata
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
        parsed = urlparse(self.path)
        if parsed.path == "/check-metadata":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            item = json.loads(body)
            try:
                check_required_metadata(item)
            except KeyError as exc:
                self._send_json({"error": str(exc)}, status=400)
            else:
                self._send_json({"ok": True})
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/request-approval"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            parts = parsed.path.split("/")
            uuid_part = parts[2]
            item = self.store.get(uuid_part)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            timestamp = data.get("timestamp")
            user_uuid = data.get("user_uuid")
            if not timestamp or not user_uuid:
                self._send_json({"error": "invalid data"}, status=400)
                return
            full_item = dict(item, metadata=self.metadata_store.get(uuid_part, {}))
            request_approval(full_item, {"uuid": user_uuid}, timestamp)
            self.store[uuid_part] = {k: v for k, v in full_item.items() if k != "metadata"}
            self.metadata_store[uuid_part] = full_item["metadata"]
            self._send_json(full_item)
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/start-draft"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            parts = parsed.path.split("/")
            uuid_part = parts[2]
            item = self.store.get(uuid_part)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            timestamp = data.get("timestamp")
            user_uuid = data.get("user_uuid")
            if not timestamp or not user_uuid:
                self._send_json({"error": "invalid data"}, status=400)
                return
            full_item = dict(item, metadata=self.metadata_store.get(uuid_part, {}))
            try:
                start_draft(full_item, {"uuid": user_uuid}, timestamp)
            except PermissionError as exc:
                self._send_json({"error": str(exc)}, status=403)
                return
            self.store[uuid_part] = {k: v for k, v in full_item.items() if k != "metadata"}
            self.metadata_store[uuid_part] = full_item["metadata"]
            self._send_json(full_item)
            return
        if parsed.path != "/content":
            self._send_json({"error": "not found"}, status=404)
            return
        if not self._authenticate():
            self._send_json({"error": "unauthorized"}, status=401)
            return
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)
        item = json.loads(body)
        item_type = item.get("type")
        if item_type not in self.valid_types:
            self._send_json({"error": "invalid type"}, status=400)
            return

        item_uuid = item.get("uuid")
        if not item_uuid:
            item_uuid = str(uuid.uuid4())
            item["uuid"] = item_uuid

        # PDFs should start in Draft/pre-submission state
        if item.get("type") == "pdf":
            item["state"] = "Draft"
            item["pre_submission"] = True

        metadata = item.get("metadata", {})
        item_no_meta = {k: v for k, v in item.items() if k != "metadata"}
        self.store[item_uuid] = item_no_meta
        self.metadata_store[item_uuid] = metadata
        response = dict(item_no_meta, metadata=metadata)
        self._send_json(response, status=201)

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
            existing = self.store[uuid]
            if item.get("type") != existing.get("type"):
                self._send_json({"error": "type cannot be modified"}, status=400)
                return
            # Ignore any incoming metadata changes
            updated = {k: v for k, v in item.items() if k != "metadata"}
            metadata = self.metadata_store.get(uuid, {})
            self.store[uuid] = updated
            self.metadata_store[uuid] = metadata
            response = dict(updated, metadata=metadata)
            self._send_json(response)
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
                self.metadata_store.pop(uuid, None)
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
