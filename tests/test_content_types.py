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
