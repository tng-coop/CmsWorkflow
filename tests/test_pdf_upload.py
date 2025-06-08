import base64
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
    pdf_bytes = b"%PDF-1.1\n1 0 obj\n<<>>\nendobj\nstartxref\n0\n%%EOF\n"
    encoded = base64.b64encode(pdf_bytes).decode()

    content = {
        "title": "PDF Upload",
        "type": ContentType.PDF.value,
        "file": encoded,
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
    assert body["file"] == encoded
    assert "uuid" in body and body["uuid"]
    assert body["state"] == "Draft"
    assert body["pre_submission"] is True
