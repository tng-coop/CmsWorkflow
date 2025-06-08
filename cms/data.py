from .types import ContentType


def seed_users():
    """Return a dictionary of example users."""
    return {
        "editor": {"uuid": "1111-1111-1111-1111", "role": "editor"},
        "admin": {"uuid": "2222-2222-2222-2222", "role": "admin"},
    }


def sample_content(users):
    """Create example HTML content using the provided users."""
    return {
        "uuid": "12345",
        "title": "Sample HTML Content",
        "type": ContentType.HTML.value,
        "metadata": {
            "created_by": users["editor"]["uuid"],
            "created_at": "2025-06-08T12:00:00",
            "edited_by": None,
            "edited_at": None,
            "draft_requested_by": None,
            "draft_requested_at": None,
            "approved_by": None,
            "approved_at": None,
            "timestamps": "2025-06-08T12:00:00",
        },
        "state": "Draft",
        "archived": False,
    }
