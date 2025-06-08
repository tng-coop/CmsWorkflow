from .types import ContentType
from .models import HTMLContent, Revision


def seed_users():
    """Return a dictionary of example users."""
    return {
        "editor": {"uuid": "1111-1111-1111-1111", "role": "editor"},
        "admin": {"uuid": "2222-2222-2222-2222", "role": "admin"},
    }


def sample_content(users):
    """Create example HTML content using the provided users."""
    timestamp = "2025-06-08T12:00:00"
    revision_uuid = "rev-12345"
    revision = Revision(
        uuid=revision_uuid,
        last_updated=timestamp,
        attributes={"title": "Sample HTML Content"},
    )
    return HTMLContent(
        uuid="12345",
        title="Sample HTML Content",
        created_by=users["editor"]["uuid"],
        created_at=timestamp,
        timestamps=timestamp,
        revisions=[revision],
    )
