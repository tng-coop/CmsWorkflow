import json
import uuid
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse

from .types import ContentType
from .workflow import (
    check_required_metadata,
    request_approval,
    start_draft,
    archive_content,
    approve_content,
)


class SimpleCRUDHandler(BaseHTTPRequestHandler):
    """Serve a very small CRUD API for content items.

    The handler validates that the ``type`` field of incoming data matches one
    of the values defined in :class:`cms.types.ContentType`.
    """

    store = {}
    categories = {}
    tokens = {}
    valid_types = {ct.value for ct in ContentType}

    @staticmethod
    def _sorted_categories():
        def sort_key(cat):
            prio = cat.get("display_priority", 0)
            if prio and prio > 0:
                return (0, prio)
            return (1, cat.get("name", "").lower())

        categories = [
            c for c in SimpleCRUDHandler.categories.values() if not c.get("archived")
        ]
        categories.sort(key=sort_key)
        return categories

    @staticmethod
    def _valid_flat_category_list(categories):
        """Return True if ``categories`` is a flat list of strings."""
        if categories is None:
            return True
        if not isinstance(categories, list):
            return False
        return all(isinstance(cat, str) for cat in categories)

    @staticmethod
    def _ensure_revision_structure(item):
        """Populate revision fields if missing."""
        if "revisions" not in item or not item["revisions"]:
            rev_uuid = str(uuid.uuid4())
            ts = item.get("timestamps") or item.get("metadata", {}).get("timestamps")
            item["revisions"] = [{"uuid": rev_uuid, "last_updated": ts}]
        else:
            for rev in item["revisions"]:
                rev.setdefault(
                    "last_updated", item.get("timestamps") or item.get("metadata", {}).get("timestamps")
                )

    @staticmethod
    def _add_revision(item):
        """Append a new revision entry reflecting the current content."""
        rev_uuid = str(uuid.uuid4())
        ts = (
            item.get("edited_at")
            or item.get("timestamps")
            or item.get("metadata", {}).get("edited_at")
            or item.get("metadata", {}).get("timestamps")
        )
        attrs = {}
        if "title" in item:
            attrs["title"] = item["title"]
        if "file" in item:
            attrs["file"] = item["file"]
        item.setdefault("revisions", [])
        item["revisions"].append({"uuid": rev_uuid, "last_updated": ts, "attributes": attrs})
        item["review_revision"] = rev_uuid

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
        if parsed.path == "/categories":
            cats = self._sorted_categories()
            self._send_json(cats)
            return
        if parsed.path.startswith("/categories/"):
            cat_uuid = parsed.path.split("/")[-1]
            cat = self.categories.get(cat_uuid)
            if cat is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(cat)
            return
        if parsed.path == "/content-types":
            self._send_json(sorted(self.valid_types))
            return
        if parsed.path.startswith("/content-types/"):
            item_type = parsed.path.split("/")[-1]
            if item_type not in self.valid_types:
                self._send_json({"error": "invalid type"}, status=400)
                return
            items = [
                i
                for i in self.store.values()
                if i.get("type") == item_type
                and i.get("state") == "Published"
                and not i.get("archived")
            ]
            self._send_json(items)
            return
        if parsed.path == "/pending-approvals":
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            pending = [
                item for item in self.store.values()
                if item.get("state") == "AwaitingApproval"
            ]
            self._send_json(pending)
            return
        if parsed.path == "/content":
            published = [
                item
                for item in self.store.values()
                if item.get("state") == "Published" and not item.get("archived")
            ]
            self._send_json(published)
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
        if parsed.path == "/categories":
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            cat_uuid = data.get("uuid") or str(uuid.uuid4())
            data["uuid"] = cat_uuid
            self.categories[cat_uuid] = {
                "uuid": cat_uuid,
                "name": data.get("name", ""),
                "display_priority": int(data.get("display_priority", 0)),
                "archived": False,
            }
            self._send_json(self.categories[cat_uuid], status=201)
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
            self._ensure_revision_structure(item)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            timestamp = data.get("timestamp")
            user_uuid = data.get("user_uuid")
            if not timestamp or not user_uuid:
                self._send_json({"error": "invalid data"}, status=400)
                return
            request_approval(item, {"uuid": user_uuid}, timestamp)
            self.store[uuid_part] = item
            self._send_json(item)
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/approve"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            parts = parsed.path.split("/")
            uuid_part = parts[2]
            item = self.store.get(uuid_part)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
                return
            self._ensure_revision_structure(item)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            timestamp = data.get("timestamp")
            user_uuid = data.get("user_uuid")
            if not timestamp or not user_uuid:
                self._send_json({"error": "invalid data"}, status=400)
                return
            approve_content(item, {"uuid": user_uuid}, timestamp)
            self.store[uuid_part] = item
            self._send_json(item)
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
            self._ensure_revision_structure(item)
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            timestamp = data.get("timestamp")
            user_uuid = data.get("user_uuid")
            if not timestamp or not user_uuid:
                self._send_json({"error": "invalid data"}, status=400)
                return
            try:
                start_draft(item, {"uuid": user_uuid}, timestamp)
            except PermissionError as exc:
                self._send_json({"error": str(exc)}, status=403)
                return
            self.store[uuid_part] = item
            self._send_json(item)
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

        if not self._valid_flat_category_list(item.get("categories")):
            self._send_json(
                {"error": "categories must be a flat list of strings"}, status=400
            )
            return

        # validate required metadata on creation
        try:
            check_required_metadata(item)
        except KeyError as exc:
            self._send_json({"error": str(exc)}, status=400)
            return

        item_uuid = item.get("uuid")
        if not item_uuid:
            item_uuid = str(uuid.uuid4())
            item["uuid"] = item_uuid

        # all newly created content should begin in Draft state
        item["state"] = "Draft"

        # PDFs should start in Draft/pre-submission state
        if item.get("type") == "pdf":
            item["pre_submission"] = True

        self._ensure_revision_structure(item)

        self.store[item_uuid] = item
        self._send_json(item, status=201)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/categories/"):
            cat_uuid = parsed.path.split("/")[-1]
            if cat_uuid not in self.categories:
                self._send_json({"error": "not found"}, status=404)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            incoming = json.loads(body)
            existing = self.categories[cat_uuid]
            updated = existing.copy()
            updated.update({
                "name": incoming.get("name", existing.get("name")),
                "display_priority": int(incoming.get("display_priority", existing.get("display_priority", 0))),
            })
            self.categories[cat_uuid] = updated
            self._send_json(updated)
            return
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
            incoming = json.loads(body)

            existing = self.store[uuid]

            # type field is immutable
            new_type = incoming.get("type", existing.get("type"))
            if new_type != existing.get("type"):
                self._send_json({"error": "type cannot be changed"}, status=400)
                return

            if not self._valid_flat_category_list(incoming.get("categories")):
                self._send_json(
                    {"error": "categories must be a flat list of strings"}, status=400
                )
                return

            # metadata fields are immutable via this endpoint
            metadata_fields = {
                "created_by",
                "created_at",
                "edited_by",
                "edited_at",
                "draft_requested_by",
                "draft_requested_at",
                "approved_by",
                "approved_at",
                "timestamps",
            }

            # support old structure
            if incoming.get("metadata") is not None:
                if incoming.get("metadata") != existing.get("metadata"):
                    self._send_json({"error": "metadata immutable"}, status=400)
                    return
            else:
                for field in metadata_fields:
                    if field in incoming and incoming[field] != existing.get(field):
                        self._send_json({"error": "metadata immutable"}, status=400)
                        return

            updated = existing.copy()
            excluded = metadata_fields | {"type", "metadata", "uuid"}
            updated.update({k: v for k, v in incoming.items() if k not in excluded})
            self._ensure_revision_structure(updated)
            self._add_revision(updated)
            self.store[uuid] = updated
            self._send_json(updated)
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/categories/"):
            cat_uuid = parsed.path.split("/")[-1]
            cat = self.categories.get(cat_uuid)
            if cat is not None:
                cat["archived"] = True
                self.categories[cat_uuid] = cat
                self._send_json(cat)
            else:
                self._send_json({"error": "not found"}, status=404)
            return
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            if uuid in self.store:
                item = self.store[uuid]
                archive_content(item)
                self.store[uuid] = item
                self._send_json(item)
            else:
                self._send_json({"error": "not found"}, status=404)
        else:
            self._send_json({"error": "not found"}, status=404)


def start_test_server(port=0):
    """Start the CRUD HTTP server on a background thread."""
    SimpleCRUDHandler.store = {}
    SimpleCRUDHandler.categories = {}
    SimpleCRUDHandler.tokens = {}
    server = HTTPServer(("localhost", port), SimpleCRUDHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
