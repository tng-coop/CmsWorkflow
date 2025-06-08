import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.api import start_test_server
from cms.data import seed_users, sample_content


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


def test_category_crud_flow():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"

    status, body = _request(base_url, "POST", "/categories", {"name": "News", "display_priority": 1})
    assert status == 201
    cat_uuid = body["uuid"]

    status, body = _request(base_url, "GET", f"/categories/{cat_uuid}")
    assert status == 200 and body["name"] == "News"

    status, body = _request(base_url, "PUT", f"/categories/{cat_uuid}", {"name": "Updates"})
    assert status == 200 and body["name"] == "Updates"

    status, body = _request(base_url, "DELETE", f"/categories/{cat_uuid}")
    assert status == 200

    status, body = _request(base_url, "GET", f"/categories/{cat_uuid}")
    server.shutdown()
    thread.join()
    assert status == 404


def test_category_sort_order():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"

    _request(base_url, "POST", "/categories", {"uuid": "1", "name": "Bananas"})
    _request(base_url, "POST", "/categories", {"uuid": "2", "name": "Apples"})
    _request(base_url, "POST", "/categories", {"uuid": "3", "name": "Zebras", "display_priority": 1})

    status, body = _request(base_url, "GET", "/categories")
    server.shutdown()
    thread.join()

    uuids = [c["uuid"] for c in body]
    assert uuids == ["3", "2", "1"]


def test_content_with_categories():
    server, thread = start_test_server()
    base_url = f"http://localhost:{server.server_port}"
    users = seed_users()
    status, token_body = _request(base_url, "POST", "/test-token", {"username": "t"})
    assert status == 200
    token = token_body["token"]

    status, body = _request(base_url, "POST", "/categories", {"name": "A"})
    cat1 = body["uuid"]
    status, body = _request(base_url, "POST", "/categories", {"name": "B"})
    cat2 = body["uuid"]

    content = sample_content(users).to_dict()
    content["categories"] = [cat1, cat2]

    status, body = _request(base_url, "POST", "/content", content, token=token)
    assert status == 201
    assert body["categories"] == [cat1, cat2]

    status, body = _request(base_url, "GET", f"/content/{content['uuid']}", token=token)
    server.shutdown()
    thread.join()
    assert status == 200
    assert body["categories"] == [cat1, cat2]
