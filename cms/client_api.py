import json
import logging
from typing import Optional
from urllib import request, parse, error

logger = logging.getLogger(__name__)


class ApiClient:
    """Simple HTTP client for the CMS test server."""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = token
        self.username: Optional[str] = None

    def _make_request(self, method: str, path: str, data=None, token: Optional[str] = None):
        url = self.base_url + path
        headers = {}
        current_token = token or self.token
        if current_token:
            headers["Authorization"] = f"Bearer {current_token}"
        body = None
        if data is not None:
            body = json.dumps(data).encode()
            headers["Content-Type"] = "application/json"

        logger.debug("HTTP %s %s", method, url)
        if headers:
            logger.debug("Request headers: %s", headers)
        if body is not None:
            logger.debug("Request body: %s", body.decode())

        req = request.Request(url, data=body, headers=headers, method=method)
        try:
            with request.urlopen(req) as resp:
                resp_body = resp.read().decode()
                logger.debug("Response status: %s", resp.status)
                logger.debug("Response body: %s", resp_body)
                return json.loads(resp_body)
        except error.HTTPError as exc:
            err_body = exc.read().decode()
            logger.debug("HTTPError %s: %s", exc.code, err_body)
            raise

    def get(self, path: str, token: Optional[str] = None):
        return self._make_request("GET", path, token=token)

    def post(self, path: str, data, token: Optional[str] = None):
        return self._make_request("POST", path, data=data, token=token)

    def put(self, path: str, data, token: Optional[str] = None):
        return self._make_request("PUT", path, data=data, token=token)

    def delete(self, path: str, token: Optional[str] = None):
        return self._make_request("DELETE", path, token=token)

    # Convenience helpers
    def create_token(self, username: str) -> str:
        resp = self.post("/test-token", {"username": username})
        self.token = resp["token"]
        self.username = username
        return self.token

    def logout(self):
        """Clear the current authentication token."""
        self.token = None
        self.username = None

    def get_content_types(self):
        return self.get("/content-types")

    def list_content_by_type(self, content_type: str):
        # Content types may contain spaces (e.g. "event schedule").
        # ``urllib.request`` does not allow spaces in the request path, so we
        # percent-encode the value.  The server will decode it again.
        encoded = parse.quote(content_type, safe="")
        return self.get(f"/content-types/{encoded}")

    def get_content(self, uuid: str):
        return self.get(f"/content/{uuid}", token=self.token)

    def create_content(self, item: dict, token: Optional[str] = None):
        return self.post("/content", item, token=token or self.token)

    def request_approval(self, uuid: str, timestamp: str, user_uuid: str, token: Optional[str] = None):
        data = {"timestamp": timestamp, "user_uuid": user_uuid}
        return self.post(f"/content/{uuid}/request-approval", data, token=token or self.token)

    def approve_content(self, uuid: str, timestamp: str, user_uuid: str, token: Optional[str] = None):
        data = {"timestamp": timestamp, "user_uuid": user_uuid}
        return self.post(f"/content/{uuid}/approve", data, token=token or self.token)

    def start_draft(self, uuid: str, timestamp: str, user_uuid: str, token: Optional[str] = None):
        data = {"timestamp": timestamp, "user_uuid": user_uuid}
        return self.post(f"/content/{uuid}/start-draft", data, token=token or self.token)


# Seeder --------------------------------------------------------------
from .data import seed_users, seed_example_contents

def seed_server(api: ApiClient):
    """Populate the running API server using the built-in seed data."""
    users = seed_users()
    contents = seed_example_contents(users)
    token_editor = api.create_token("editor")
    for item in contents:
        api.create_content(item.to_dict(), token=token_editor)
    api.token = token_editor
    api.username = "editor"
    return users
