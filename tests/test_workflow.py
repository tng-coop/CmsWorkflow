import json
import os
import sys
import urllib.error
import urllib.request

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users, sample_content
from cms.workflow import (
    check_required_metadata,
    pending_approvals,
    request_approval,
    start_draft,
)
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


def _request(base_url, method, path, data=None):
    url = base_url + path
    headers = {"Content-Type": "application/json"}
    if data is not None:
        data = json.dumps(data).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def test_editor_does_not_submit_content_admin_sees_nothing(content_html):
    contents = [content_html]
    pending = pending_approvals(contents)
    assert pending == []


def test_request_approval_adds_to_pending(content_html, users):
    timestamp = "2025-06-09T10:00:00"
    request_approval(content_html, users["editor"], timestamp)
    assert pending_approvals([content_html]) == [content_html]


def test_check_required_metadata_success(content_html):
    check_required_metadata(content_html)


def test_export_json_missing_metadata(users):
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

    with pytest.raises(KeyError):
        check_required_metadata(invalid_content)


def test_draft_locked_for_other_user(content_html, users):
    ts1 = "2025-06-10T09:00:00"
    start_draft(content_html, users["editor"], ts1)

    with pytest.raises(PermissionError) as excinfo:
        start_draft(content_html, users["admin"], "2025-06-10T10:00:00")

    assert users["editor"]["uuid"] in str(excinfo.value)


def test_crud_flow(api_server, content_html):
    # CREATE
    status, body = _request(api_server, "POST", "/content", content_html)
    assert status == 201
    assert body["uuid"] == content_html["uuid"]

    # READ
    status, body = _request(api_server, "GET", f"/content/{content_html['uuid']}")
    assert status == 200
    assert body["uuid"] == content_html["uuid"]

    # UPDATE
    updated = body.copy()
    updated["title"] = "Updated"
    status, body = _request(api_server, "PUT", f"/content/{updated['uuid']}", updated)
    assert status == 200
    assert body["title"] == "Updated"

    # DELETE
    status, body = _request(api_server, "DELETE", f"/content/{updated['uuid']}")
    assert status == 200
    assert body["deleted"] == updated["uuid"]

    # Confirm deletion
    status, _ = _request(api_server, "GET", f"/content/{updated['uuid']}")
    assert status == 404
