import json
from typing import Optional
from urllib import request, parse


class ApiClient:
    """Simple HTTP client for the CMS test server."""

    def __init__(self, base_url: str, token: Optional[str] = None):
        self.base_url = base_url.rstrip("/")
        self.token: Optional[str] = token

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
        req = request.Request(url, data=body, headers=headers, method=method)
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode())

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
        return self.token

    def get_content_types(self):
        return self.get("/content-types")

    def list_content_by_type(self, content_type: str):
        quoted = parse.quote(content_type)
        return self.get(f"/content-types/{quoted}")

    def get_content(self, uuid: str):
        return self.get(f"/content/{uuid}", token=self.token)

    def create_content(self, item: dict):
        return self.post("/content", item, token=self.token)


# Seeder --------------------------------------------------------------
from .data import seed_users, seed_example_contents

def seed_server(api: ApiClient):
    """Populate the running API server using the built-in seed data."""
    users = seed_users()
    contents = seed_example_contents(users)
    api.create_token("editor")
    for item in contents:
        api.create_content(item.to_dict())
    return users
