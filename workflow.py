import unittest
import json
from datetime import datetime

class TestCMSWorkflow(unittest.TestCase):

    def setUp(self):
        # Seed Users (Editor and Admin), using UUID for identification
        self.users = {
            "editor": {"uuid": "1111-1111-1111-1111", "role": "editor"},
            "admin": {"uuid": "2222-2222-2222-2222", "role": "admin"},
            "anonymous": {"uuid": None, "role": "anonymous"}  # Anonymous readers have no UUID
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
        
        self.content_pdf = {
            "uuid": "12346",
            "title": "Sample PDF Content",
            "type": "PDF",  # Data type is now PDF
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

        self.content_office_address = {
            "uuid": "12347",
            "title": "Sample Office Address",
            "type": "OFFICE_ADDRESS",  # Data type is now OFFICE_ADDRESS
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

        self.content_event_schedule = {
            "uuid": "12348",
            "title": "Sample Event Schedule",
            "type": "EVENT_SCHEDULE",  # Data type is now EVENT_SCHEDULE
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
        self.draft_content_pdf = self.content_pdf.copy()
        self.draft_content_office_address = self.content_office_address.copy()
        self.draft_content_event_schedule = self.content_event_schedule.copy()

    def test_create_draft(self):
        """Test creating a new draft version of content with different data types."""
        self.assertEqual(self.draft_content_html['state'], 'Draft')
        self.assertEqual(self.draft_content_pdf['state'], 'Draft')
        self.assertEqual(self.draft_content_office_address['state'], 'Draft')
        self.assertEqual(self.draft_content_event_schedule['state'], 'Draft')

        self.assertEqual(self.draft_content_html['uuid'], self.content_html['uuid'])
        self.assertEqual(self.draft_content_pdf['uuid'], self.content_pdf['uuid'])
        self.assertEqual(self.draft_content_office_address['uuid'], self.content_office_address['uuid'])
        self.assertEqual(self.draft_content_event_schedule['uuid'], self.content_event_schedule['uuid'])

        # Ensure creation metadata is set
        self.assertEqual(self.draft_content_html['metadata']['created_by'], self.users["editor"]["uuid"])
        self.assertIsNotNone(self.draft_content_html['metadata']['created_at'])

    def test_request_merge(self):
        """Test that a draft editor can request a merge for different content types."""
        self.draft_content_html['state'] = 'ReviewRequested'
        self.draft_content_pdf['state'] = 'ReviewRequested'
        self.draft_content_office_address['state'] = 'ReviewRequested'
        self.draft_content_event_schedule['state'] = 'ReviewRequested'

        # Add who requested the draft and when
        self.draft_content_html['metadata']['draft_requested_by'] = self.users["editor"]["uuid"]
        self.draft_content_html['metadata']['draft_requested_at'] = datetime.now().isoformat()

        self.assertEqual(self.draft_content_html['state'], 'ReviewRequested')
        self.assertEqual(self.draft_content_pdf['state'], 'ReviewRequested')
        self.assertEqual(self.draft_content_office_address['state'], 'ReviewRequested')
        self.assertEqual(self.draft_content_event_schedule['state'], 'ReviewRequested')

        self.assertEqual(self.draft_content_html['metadata']['draft_requested_by'], self.users["editor"]["uuid"])

    def test_approve_content(self):
        """Test approving content, transitioning it to 'Approved' (final published state) for different types."""
        # Simulate transition to "ReviewRequested" before approval
        self.draft_content_html['state'] = 'ReviewRequested'
        self.draft_content_pdf['state'] = 'ReviewRequested'
        self.draft_content_office_address['state'] = 'ReviewRequested'
        self.draft_content_event_schedule['state'] = 'ReviewRequested'

        # Simulate approval (final state, treated as published)
        self.draft_content_html['metadata']['approved_by'] = self.users["admin"]["uuid"]
        self.draft_content_html['metadata']['approved_at'] = datetime.now().isoformat()

        self.draft_content_html['state'] = 'Approved'
        self.assertEqual(self.draft_content_html['state'], 'Approved')
        self.assertEqual(self.draft_content_html['metadata']['approved_by'], self.users["admin"]["uuid"])

    def test_archive_content(self):
        """Test archiving content (soft delete) for different content types."""
        self.draft_content_html['archived'] = True
        self.draft_content_pdf['archived'] = True
        self.draft_content_office_address['archived'] = True
        self.draft_content_event_schedule['archived'] = True

        self.assertTrue(self.draft_content_html['archived'])
        self.assertTrue(self.draft_content_pdf['archived'])
        self.assertTrue(self.draft_content_office_address['archived'])
        self.assertTrue(self.draft_content_event_schedule['archived'])

    def test_export_json(self):
        """Test exporting content as JSON for different data types."""
        content_json_html = json.dumps(self.draft_content_html)
        content_json_pdf = json.dumps(self.draft_content_pdf)
        content_json_office_address = json.dumps(self.draft_content_office_address)
        content_json_event_schedule = json.dumps(self.draft_content_event_schedule)

        self.assertIsInstance(content_json_html, str)
        self.assertIsInstance(content_json_pdf, str)
        self.assertIsInstance(content_json_office_address, str)
        self.assertIsInstance(content_json_event_schedule, str)

        self.assertIn('uuid', content_json_html)
        self.assertIn('title', content_json_html)
        self.assertIn('type', content_json_html)  # Check for type field

        self.assertIn('uuid', content_json_pdf)
        self.assertIn('title', content_json_pdf)
        self.assertIn('type', content_json_pdf)  # Check for type field

        self.assertIn('uuid', content_json_office_address)
        self.assertIn('title', content_json_office_address)
        self.assertIn('type', content_json_office_address)  # Check for type field

        self.assertIn('uuid', content_json_event_schedule)
        self.assertIn('title', content_json_event_schedule)
        self.assertIn('type', content_json_event_schedule)  # Check for type field

if __name__ == '__main__':
    unittest.main()

