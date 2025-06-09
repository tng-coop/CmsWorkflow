import uuid
import json
import os
import sys
import urllib.error
import urllib.request

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


def test_upload_pdf_content(api_server, auth_token, users):
    file_id = str(uuid.uuid4())

    content = {
        "title": "PDF Upload",
        "type": ContentType.PDF.value,
        "file_uuid": file_id,
        "created_by": users["editor"]["uuid"],
        "created_at": "2025-06-09T12:00:00",
        "edited_by": None,
        "edited_at": None,
        "draft_requested_by": None,
        "draft_requested_at": None,
        "approved_by": None,
        "approved_at": None,
        "timestamps": "2025-06-09T12:00:00",
    }

    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    assert body["type"] == ContentType.PDF.value
    assert "file_uuid" not in body
    latest_rev = body["revisions"][-1]
    assert latest_rev["attributes"]["file_uuid"] == file_id
    assert "uuid" in body and body["uuid"]
    assert body["is_published"] is False
    assert body["review_requested"] is False
    assert body.get("published_revision") is None
    assert body.get("review_revision") is None
