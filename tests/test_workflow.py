import json
import os
import sys
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users, sample_content
from cms.api import start_test_server


@pytest.fixture()
def users():
    return seed_users()


@pytest.fixture()
def content_html(users):
    return sample_content(users)


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
    assert body["state"] == "AwaitingApproval"

    status, body = _request(api_server, "GET", "/pending-approvals", token=auth_token)
    assert status == 200
    assert len(body) == 1 and body[0]["uuid"] == content_html["uuid"]


def test_check_required_metadata_success(api_server, content_html, auth_token):
    status, body = _request(api_server, "POST", "/check-metadata", content_html, token=auth_token)
    assert status == 200
    assert body == {"ok": True}


def test_export_json_missing_metadata(api_server, users, auth_token):
    invalid_content = {
        "uuid": "12350",
        "title": "Missing Metadata Content",
        "type": "HTML",
        "metadata": {
            "created_by": users["editor"]["uuid"],
            # Missing 'created_at' and 'timestamps'
        },
        "state": "Draft",
        "archived": False,
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

    # DELETE
    status, body = _request(api_server, "DELETE", f"/content/{updated['uuid']}", token=auth_token)
    assert status == 200
    assert body["deleted"] == updated["uuid"]

    # Confirm deletion
    status, _ = _request(api_server, "GET", f"/content/{updated['uuid']}", token=auth_token)
    assert status == 404
