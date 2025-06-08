import unittest
import json
from datetime import datetime


class TestCMSWorkflow(unittest.TestCase):

    def setUp(self):
        # Seed Users (Editor and Admin), using UUID for identification
        self.users = {
            "editor": {"uuid": "1111-1111-1111-1111", "role": "editor"},
            "admin": {"uuid": "2222-2222-2222-2222", "role": "admin"}
        }

        # Sample content data to work with, now supporting multiple types and new metadata
        self.content_html = {
            "uuid": "12345",
            "title": "Sample HTML Content",
            "type": "HTML",  # Data type is now HTML
            "metadata": {
                "created_by": self.users["editor"]["uuid"],
                "created_at": "2025-06-08T12:00:00",
                "edited_by": None,
                "edited_at": None,
                "draft_requested_by": None,
                "draft_requested_at": None,
                "approved_by": None,
                "approved_at": None,
                "timestamps": "2025-06-08T12:00:00"
            },
            "state": "Draft",
            "archived": False,
        }

        # Make copies for the draft content to modify during tests
        self.draft_content_html = self.content_html.copy()

    def check_required_metadata(self, content):
        """Helper function to check if required metadata fields are present."""
        required_fields = ["created_by", "created_at", "timestamps"]
        for field in required_fields:
            if field not in content["metadata"] or content["metadata"][field] is None:
                raise KeyError(f"Missing required metadata field: {field}")

    def test_export_json_missing_metadata(self):
        """Test exporting content that has missing metadata fields."""
        # Remove some metadata fields for the test
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

        # Check that the required metadata is missing and raise a KeyError
        with self.assertRaises(KeyError, msg="Missing required metadata fields."):
            self.check_required_metadata(invalid_content)  # This should raise a KeyError

        # Now try to export content with missing metadata, this will manually raise an error before serialization
        with self.assertRaises(KeyError, msg="Missing required metadata fields."):
            # Check metadata first before serializing
            self.check_required_metadata(invalid_content)  # This will raise a KeyError due to missing fields
            json.dumps(invalid_content)  # We don't need to serialize if metadata is missing, but this line ensures no further code execution

if __name__ == '__main__':
    unittest.main()

