import json
import unittest

from cms.data import seed_users, sample_content
from cms.workflow import check_required_metadata


class TestCMSWorkflow(unittest.TestCase):
    def setUp(self):
        self.users = seed_users()
        self.content_html = sample_content(self.users)
        self.draft_content_html = self.content_html.copy()

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


if __name__ == "__main__":
    unittest.main()
