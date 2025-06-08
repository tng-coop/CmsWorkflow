import json
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import urlparse, unquote

from .types import ContentType
from .workflow import check_required_metadata
from .db_context import DbContext
from .services import CategoryService, ContentService, TokenService


class SimpleCRUDHandler(BaseHTTPRequestHandler):
    """Serve a very small CRUD API for content items.

    The handler validates that the ``type`` field of incoming data matches one
    of the values defined in :class:`cms.types.ContentType`.
    """

    context: DbContext
    content_service: ContentService
    category_service: CategoryService
    token_service: TokenService

    # Backwards compatible references to the underlying stores
    store: dict
    categories: dict
    tokens: dict

    valid_types = {ct.value for ct in ContentType}

    def _sorted_categories(self):
        return self.category_service.list_categories()

    @staticmethod
    def _valid_flat_category_list(categories):
        """Return True if ``categories`` is a flat list of strings."""
        if categories is None:
            return True
        if not isinstance(categories, list):
            return False
        return all(isinstance(cat, str) for cat in categories)


    def _authenticate(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return False
        token = auth.split(" ", 1)[1]
        return self.token_service.validate_token(token)

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
            cat = self.category_service.get_category(cat_uuid)
            if cat is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(cat)
            return
        if parsed.path == "/content-types":
            self._send_json(sorted(self.valid_types))
            return
        if parsed.path.startswith("/content-types/"):
            # decode any percent-encoding to allow client requests that
            # properly escape spaces in content type values
            item_type = unquote(parsed.path.split("/")[-1])
            if item_type not in self.valid_types:
                self._send_json({"error": "invalid type"}, status=400)
                return
            authenticated = self._authenticate()
            items = self.content_service.list_by_type(item_type, authenticated)
            self._send_json(items)
            return
        if parsed.path == "/pending-approvals":
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            pending = self.content_service.pending_approvals()
            self._send_json(pending)
            return
        if parsed.path == "/content":
            authenticated = self._authenticate()
            items = self.content_service.list_all(authenticated)
            self._send_json(items)
            return
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid_str = parsed.path.split("/")[-1]
            item = self.content_service.get(uuid_str)
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
            token = self.token_service.create_token(username)
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
            category = self.category_service.create_category(data)
            self._send_json(category, status=201)
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/request-approval"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid_part = parsed.path.split("/")[2]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            item = self.content_service.request_approval(uuid_part, data)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(item)
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/approve"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid_part = parsed.path.split("/")[2]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            item = self.content_service.approve(uuid_part, data)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(item)
            return
        if parsed.path.startswith("/content/") and parsed.path.endswith("/start-draft"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid_part = parsed.path.split("/")[2]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            data = json.loads(body)
            try:
                item = self.content_service.start_draft(uuid_part, data)
            except PermissionError as exc:
                self._send_json({"error": str(exc)}, status=403)
                return
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
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

        created = self.content_service.create(item)
        self._send_json(created, status=201)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/categories/"):
            cat_uuid = parsed.path.split("/")[-1]
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            incoming = json.loads(body)
            updated = self.category_service.update_category(cat_uuid, incoming)
            if updated is None:
                self._send_json({"error": "not found"}, status=404)
            else:
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

            if not self._valid_flat_category_list(incoming.get("categories")):
                self._send_json(
                    {"error": "categories must be a flat list of strings"}, status=400
                )
                return

            try:
                updated = self.content_service.update(uuid, incoming)
            except ValueError as exc:
                self._send_json({"error": str(exc)}, status=400)
                return

            if updated is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(updated)
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/categories/"):
            cat_uuid = parsed.path.split("/")[-1]
            cat = self.category_service.archive_category(cat_uuid)
            if cat is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(cat)
            return
        if parsed.path.startswith("/content/"):
            if not self._authenticate():
                self._send_json({"error": "unauthorized"}, status=401)
                return
            uuid = parsed.path.split("/")[-1]
            item = self.content_service.archive(uuid)
            if item is None:
                self._send_json({"error": "not found"}, status=404)
            else:
                self._send_json(item)
        else:
            self._send_json({"error": "not found"}, status=404)


def start_test_server(port=0):
    """Start the CRUD HTTP server on a background thread."""
    context = DbContext()
    SimpleCRUDHandler.context = context
    SimpleCRUDHandler.content_service = ContentService(context)
    SimpleCRUDHandler.category_service = CategoryService(context)
    SimpleCRUDHandler.token_service = TokenService(context)
    # expose raw stores for backward compatibility
    SimpleCRUDHandler.store = context.contents
    SimpleCRUDHandler.categories = context.categories
    SimpleCRUDHandler.tokens = context.tokens
    server = HTTPServer(("localhost", port), SimpleCRUDHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread
