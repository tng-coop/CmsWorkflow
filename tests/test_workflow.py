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
def content_html(users):
    return sample_content(users).to_dict()


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


def test_editor_does_not_submit_content_admin_sees_nothing(api_server, content_html, auth_token):
    # create content but do not request approval
    status, _ = _request(api_server, "POST", "/content", content_html, token=auth_token)
    assert status == 201

    status, body = _request(api_server, "GET", "/pending-approvals", token=auth_token)
    assert status == 200
    assert body == []


def test_request_approval_adds_to_pending(api_server, content_html, users, auth_token):
    status, _ = _request(api_server, "POST", "/content", content_html, token=auth_token)
    assert status == 201
    timestamp = "2025-06-09T10:00:00"
    data = {"timestamp": timestamp, "user_uuid": users["editor"]["uuid"]}
    status, body = _request(
        api_server,
        "POST",
        f"/content/{content_html['uuid']}/request-approval",
        data,
        token=auth_token,
    )
    assert status == 200
    assert body["draft_requested_by"] == users["editor"]["uuid"]
    assert body["is_published"] is False
    assert body["review_requested"] is True

    status, body = _request(api_server, "GET", "/pending-approvals", token=auth_token)
    assert status == 200
    assert len(body) == 1 and body[0]["uuid"] == content_html["uuid"]


def test_check_required_metadata_success(api_server, content_html, auth_token):
    status, body = _request(api_server, "POST", "/check-metadata", content_html, token=auth_token)
    assert status == 200
    assert body == {"ok": True}


def test_content_created_without_state_starts_in_draft(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    content.pop("state", None)
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    assert body["is_published"] is False
    assert body["review_requested"] is False
    assert body.get("published_revision") is None
    assert body.get("review_revision") is None


def test_content_state_overridden_to_draft(api_server, content_html, auth_token):
    content_html["state"] = "Published"
    status, body = _request(api_server, "POST", "/content", content_html, token=auth_token)
    assert status == 201
    assert body["is_published"] is False
    assert body["review_requested"] is False
    assert body.get("published_revision") is None
    assert body.get("review_revision") is None


def test_export_json_missing_metadata(api_server, users, auth_token):
    invalid_content = {
        "uuid": str(uuid.uuid4()),
        "title": "Missing Metadata Content",
        "type": "HTML",
        "created_by": users["editor"]["uuid"],
        # Missing 'created_at' and 'timestamps'
        "state": "Draft",
    }

    status, body = _request(api_server, "POST", "/check-metadata", invalid_content, token=auth_token)
    assert status == 400
    assert "Missing required metadata field" in body["error"]


def test_draft_locked_for_other_user(api_server, content_html, users, auth_token):
    status, _ = _request(api_server, "POST", "/content", content_html, token=auth_token)
    assert status == 201
    ts1 = "2025-06-10T09:00:00"
    data = {"timestamp": ts1, "user_uuid": users["editor"]["uuid"]}
    status, _ = _request(
        api_server,
        "POST",
        f"/content/{content_html['uuid']}/start-draft",
        data,
        token=auth_token,
    )
    assert status == 200
    data = {"timestamp": "2025-06-10T10:00:00", "user_uuid": users["admin"]["uuid"]}
    status, body = _request(
        api_server,
        "POST",
        f"/content/{content_html['uuid']}/start-draft",
        data,
        token=auth_token,
    )
    assert status == 403
    assert users["editor"]["uuid"] in body["error"]


def test_crud_flow(api_server, content_html, auth_token):
    # CREATE
    status, body = _request(api_server, "POST", "/content", content_html, token=auth_token)
    assert status == 201
    assert body["uuid"] == content_html["uuid"]

    # READ
    status, body = _request(api_server, "GET", f"/content/{content_html['uuid']}", token=auth_token)
    assert status == 200
    assert body["uuid"] == content_html["uuid"]

    # UPDATE
    updated = body.copy()
    updated["title"] = "Updated"
    status, body = _request(api_server, "PUT", f"/content/{updated['uuid']}", updated, token=auth_token)
    assert status == 200
    assert body["title"] == "Updated"

    # ARCHIVE
    status, body = _request(api_server, "DELETE", f"/content/{updated['uuid']}", token=auth_token)
    assert status == 200
    assert body.get("published_revision") is None and body.get("review_revision") is None

    # Confirm archived item is still retrievable
    status, body = _request(api_server, "GET", f"/content/{updated['uuid']}", token=auth_token)
    assert status == 200
    assert body.get("published_revision") is None and body.get("review_revision") is None
