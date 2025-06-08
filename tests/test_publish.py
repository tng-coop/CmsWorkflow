import json
import base64
import os
import sys
import urllib.request
import urllib.error

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.api import start_test_server
from cms.data import seed_users
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


def _sample_content(content_type, users, idx):
    ts = "2025-06-08T12:00:00"
    content = {
        "uuid": f"uuid-{idx}",
        "title": f"Item {idx}",
        "type": content_type,
        "created_by": users["editor"]["uuid"],
        "created_at": ts,
        "timestamps": ts,
    }
    if content_type == ContentType.PDF.value:
        content["file"] = base64.b64encode(b"pdf").decode()
    return content


def test_publish_and_list_public_content():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    users = seed_users()

    status, body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = body["token"]

    uuids = []
    for idx, ct in enumerate([
        ContentType.HTML.value,
        ContentType.PDF.value,
        ContentType.OFFICE_ADDRESS.value,
        ContentType.EVENT_SCHEDULE.value,
    ]):
        content = _sample_content(ct, users, idx)
        status, body = _request(base_url, "POST", "/content", content, token=token)
        assert status == 201
        uuids.append(body["uuid"])
        data = {"timestamp": "2025-06-09T10:00:00", "user_uuid": users["editor"]["uuid"]}
        status, _ = _request(base_url, "POST", f"/content/{body['uuid']}/request-approval", data, token=token)
        assert status == 200
        data = {"timestamp": "2025-06-09T11:00:00", "user_uuid": users["admin"]["uuid"]}
        status, _ = _request(base_url, "POST", f"/content/{body['uuid']}/approve", data, token=token)
        assert status == 200

    status, body = _request(base_url, "GET", "/content")
    server.shutdown()
    thread.join()
    returned = [c["uuid"] for c in body]
    assert status == 200
    assert set(returned) == set(uuids)
