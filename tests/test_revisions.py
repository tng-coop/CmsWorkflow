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
def api_server():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    yield base_url
    server.shutdown()
    thread.join()


@pytest.fixture()
def auth_token(api_server):
    status, body = _request(api_server, "POST", "/test-token", {"username": "revtester"})
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


def test_revision_history(api_server, users, auth_token):
    content = sample_content(users).to_dict()
    status, body = _request(api_server, "POST", "/content", content, token=auth_token)
    assert status == 201
    assert len(body["revisions"]) == 1
    assert body.get("review_revision") is None
    assert body.get("published_revision") is None

    for i in range(3):
        updated = body.copy()
        updated["title"] = f"Update {i}"
        status, body = _request(api_server, "PUT", f"/content/{updated['uuid']}", updated, token=auth_token)
        assert status == 200

    assert body["review_revision"] == body["revisions"][-1]["uuid"]

    assert len(body["revisions"]) == 4
