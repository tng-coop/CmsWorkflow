import json
import os
import sys
import urllib.error
import urllib.request
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users
from cms.types import ContentType
from cms.api import start_test_server


@pytest.fixture()
def users():
    return seed_users()


@pytest.fixture()
def api_server():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    yield base_url
    server.shutdown()
    thread.join()


@pytest.fixture()
def auth_token(api_server):
    status, body = _request(api_server, "POST", "/test-token", {"username": "tester"})
    assert status == 200
    return body["token"]


def _request(base_url, method, path, data=None, token=None):
    url = base_url + path
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_html_revisions_include_html_content(api_server, auth_token, users):
    content = {
        "title": "HTML Upload",
        "type": ContentType.HTML.value,
        "html_content": "<p>Hello</p>",
        "created_by": users["editor"]["uuid"],
        "created_at": "2025-06-09T12:00:00",
        "timestamps": "2025-06-09T12:00:00",
    }
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    item_uuid = body["uuid"]

    updated = body.copy()
    updated["title"] = "Updated Title"
    status, body = _request(api_server, "PUT", f"/content/{item_uuid}", updated, token=auth_token)
    assert status == 200

    status, body = _request(api_server, "GET", f"/content/{item_uuid}", token=auth_token)
    assert status == 200
    for rev in body["revisions"]:
        assert "html_content" in rev["attributes"]
