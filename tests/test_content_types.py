import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import urllib.error
import urllib.request

import pytest

from cms.api import start_test_server
from cms.data import seed_users, sample_content
from cms.types import ContentType


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


def test_supported_content_types():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    status, body = _request(base_url, "GET", "/content-types")
    server.shutdown()
    thread.join()
    expected = {"html", "pdf", "office address", "event schedule"}
    assert status == 200
    assert set(body) == expected


def test_post_invalid_content_type(tmp_path):
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    status, body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = body["token"]

    content = {"title": "Bad", "type": "unknown"}
    status, body = _request(base_url, "POST", "/content", content, token=token)
    server.shutdown()
    thread.join()
    assert status == 400
    assert body["error"] == "invalid type"

def test_type_immutable_on_update(tmp_path):
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    status, body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = body["token"]

    users = seed_users()
    content = sample_content(users).to_dict()
    status, body = _request(base_url, "POST", "/content", content, token=token)
    assert status == 201

    updated = body.copy()
    updated["type"] = ContentType.PDF.value
    status, body = _request(base_url, "PUT", f"/content/{updated['uuid']}", updated, token=token)
    server.shutdown()
    thread.join()
    assert status == 400
    assert body["error"] == "type cannot be changed"


def test_metadata_immutable_on_update(tmp_path):
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    status, body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = body["token"]

    users = seed_users()
    content = sample_content(users).to_dict()
    status, body = _request(base_url, "POST", "/content", content, token=token)
    assert status == 201

    updated = body.copy()
    updated["created_by"] = users["admin"]["uuid"]
    status, body = _request(base_url, "PUT", f"/content/{updated['uuid']}", updated, token=token)
    server.shutdown()
    thread.join()
    assert status == 400
    assert body["error"] == "metadata immutable"


def _publish_item(base_url, token, users, uuid):
    data = {"timestamp": "2025-06-09T10:00:00", "user_uuid": users["editor"]["uuid"]}
    status, _ = _request(base_url, "POST", f"/content/{uuid}/request-approval", data, token=token)
    assert status == 200
    data = {"timestamp": "2025-06-09T11:00:00", "user_uuid": users["admin"]["uuid"]}
    status, _ = _request(base_url, "POST", f"/content/{uuid}/approve", data, token=token)
    assert status == 200


def test_list_content_by_type(tmp_path):
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    users = seed_users()

    status, body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = body["token"]

    # create a category to demonstrate categories are ignored
    status, body = _request(base_url, "POST", "/categories", {"name": "C"})
    cat_uuid = body["uuid"]

    c1 = sample_content(users).to_dict()
    c1["uuid"] = "html1"
    status, _ = _request(base_url, "POST", "/content", c1, token=token)
    assert status == 201
    _publish_item(base_url, token, users, c1["uuid"])

    c2 = sample_content(users).to_dict()
    c2["uuid"] = "html2"
    c2["categories"] = [cat_uuid]
    status, _ = _request(base_url, "POST", "/content", c2, token=token)
    assert status == 201
    _publish_item(base_url, token, users, c2["uuid"])

    status, body = _request(base_url, "GET", "/content-types/html")
    server.shutdown()
    thread.join()

    returned = {item["uuid"] for item in body}
    assert status == 200
    assert returned == {"html1", "html2"}
