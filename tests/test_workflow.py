import json
import os
import sys
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users, sample_content
from cms.workflow import check_required_metadata, pending_approvals
from cms.api import start_test_server


class TestCMSWorkflow(unittest.TestCase):
    def setUp(self):
        self.users = seed_users()
        self.content_html = sample_content(self.users)
        self.draft_content_html = self.content_html.copy()

    def test_editor_does_not_submit_content_admin_sees_nothing(self):
        """Content saved as draft should not appear in admin approval queue."""
        contents = [self.content_html]
        pending = pending_approvals(contents)
        self.assertEqual(pending, [], "Admin should not see approval requests")

    def test_export_json_missing_metadata(self):
        """Test exporting content that has missing metadata fields."""
        invalid_content = {
            "uuid": "12350",
            "title": "Missing Metadata Content",
            "type": "HTML",
            "metadata": {
                "created_by": self.users["editor"]["uuid"],
                # Missing 'created_at' and 'timestamps'
            },
            "state": "Draft",
            "archived": False,
        }

        with self.assertRaises(KeyError, msg="Missing required metadata fields."):
            check_required_metadata(invalid_content)

        with self.assertRaises(KeyError, msg="Missing required metadata fields."):
            check_required_metadata(invalid_content)
            json.dumps(invalid_content)


class TestCMSAPICRUD(unittest.TestCase):
    def setUp(self):
        self.server, self.thread = start_test_server()
        self.base_url = f"http://localhost:{self.server.server_port}"
        self.users = seed_users()
        self.content = sample_content(self.users)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()

    def _request(self, method, path, data=None):
        url = self.base_url + path
        headers = {"Content-Type": "application/json"}
        if data is not None:
            data = json.dumps(data).encode()
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req) as resp:
                return resp.status, json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read().decode())

    def test_crud_flow(self):
        # CREATE
        status, body = self._request("POST", "/content", self.content)
        self.assertEqual(status, 201)
        self.assertEqual(body["uuid"], self.content["uuid"])

        # READ
        status, body = self._request("GET", f"/content/{self.content['uuid']}")
        self.assertEqual(status, 200)
        self.assertEqual(body["uuid"], self.content["uuid"])

        # UPDATE
        updated = body.copy()
        updated["title"] = "Updated"
        status, body = self._request("PUT", f"/content/{updated['uuid']}", updated)
        self.assertEqual(status, 200)
        self.assertEqual(body["title"], "Updated")

        # DELETE
        status, body = self._request("DELETE", f"/content/{updated['uuid']}")
        self.assertEqual(status, 200)
        self.assertEqual(body["deleted"], updated["uuid"])

        # Confirm deletion
        status, _ = self._request("GET", f"/content/{updated['uuid']}")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
