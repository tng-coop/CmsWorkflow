import json
import os
import sys
import urllib.error
import urllib.request
import uuid

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users, sample_content
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


# Content Creation -------------------------------------------------------------

def test_create_draft_item(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    assert body.get("uuid")
    assert body["created_by"] == content["created_by"]
    assert body["created_at"] == content["created_at"]
    assert body.get("published_revision") is None
    assert len(body["revisions"]) == 1
    assert body["is_published"] is False


def test_create_invalid_type(api_server, users, auth_token):
    ts = "2025-06-09T12:00:00"
    bad = {
        "title": "Bad",
        "type": "INVALID",
        "created_by": users["editor"]["uuid"],
        "created_at": ts,
        "timestamps": ts,
    }
    status, body = _request(api_server, "POST", "/content", bad, token=auth_token)
    assert status == 400
    assert "invalid type" in body.get("error", "")


def test_create_missing_field(api_server, users, auth_token):
    ts = "2025-06-09T12:00:00"
    incomplete = {
        "type": "html",
        "created_by": users["editor"]["uuid"],
        "created_at": ts,
        "timestamps": ts,
    }
    status, body = _request(api_server, "POST", "/content", incomplete, token=auth_token)
    assert status == 400
    assert "missing" in body.get("error", "").lower()


# Draft Editing & Revision Tracking -------------------------------------------

def test_start_editing_sets_lock(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    ts = "2025-06-10T09:00:00"
    data = {"user_uuid": users["editor"]["uuid"], "timestamp": ts}
    status, body = _request(api_server, "POST", f"/content/{body['uuid']}/start-draft", data, token=auth_token)
    assert status == 200
    assert body["edited_by"] == users["editor"]["uuid"]
    assert body["edited_at"] == ts


def test_save_multiple_draft_revisions(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    c_uuid = body["uuid"]
    ts = "2025-06-10T09:00:00"
    data = {"user_uuid": users["editor"]["uuid"], "timestamp": ts}
    status, body = _request(api_server, "POST", f"/content/{c_uuid}/start-draft", data, token=auth_token)
    assert status == 200

    updated = body.copy()
    updated["title"] = "First Edit"
    status, body = _request(api_server, "PUT", f"/content/{c_uuid}", updated, token=auth_token)
    assert status == 200
    first_count = len(body["revisions"])
    first_rev = body["revisions"][-1]["uuid"]
    assert body["review_revision"] == first_rev

    updated = body.copy()
    updated["title"] = "Second Edit"
    status, body = _request(api_server, "PUT", f"/content/{c_uuid}", updated, token=auth_token)
    assert status == 200
    assert len(body["revisions"]) == first_count + 1
    assert body["review_revision"] == body["revisions"][-1]["uuid"]


def test_prevent_concurrent_edits(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    c_uuid = body["uuid"]
    ts = "2025-06-10T09:00:00"
    data = {"user_uuid": users["editor"]["uuid"], "timestamp": ts}
    status, body = _request(api_server, "POST", f"/content/{c_uuid}/start-draft", data, token=auth_token)
    assert status == 200
    data = {"user_uuid": users["admin"]["uuid"], "timestamp": "2025-06-10T10:00:00"}
    status, body = _request(api_server, "POST", f"/content/{c_uuid}/start-draft", data, token=auth_token)
    assert status == 403
    assert users["editor"]["uuid"] in body.get("error", "")


def test_finish_editing_persists_draft_state(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    c_uuid = body["uuid"]
    ts = "2025-06-10T09:00:00"
    data = {"user_uuid": users["editor"]["uuid"], "timestamp": ts}
    status, body = _request(api_server, "POST", f"/content/{c_uuid}/start-draft", data, token=auth_token)
    assert status == 200

    updated = body.copy()
    updated["title"] = "Edited"
    status, body = _request(api_server, "PUT", f"/content/{c_uuid}", updated, token=auth_token)
    assert status == 200

    status, body = _request(api_server, "GET", f"/content/{c_uuid}", token=auth_token)
    assert status == 200
    assert body["edited_by"] == users["editor"]["uuid"]
    assert body["is_published"] is False

