from .types import ContentType
import uuid

from .models import (
    HTMLContent,
    PDFContent,
    OfficeAddressContent,
    EventScheduleContent,
    Revision,
)


def seed_users():
    """Return a dictionary of example users with generated UUIDs."""
    return {
        "editor": {"uuid": str(uuid.uuid4()), "role": "editor"},
        "admin": {"uuid": str(uuid.uuid4()), "role": "admin"},
    }


def sample_content(users):
    """Create example HTML content using the provided users."""
    timestamp = "2025-06-08T12:00:00"
    revision_uuid = str(uuid.uuid4())
    revision = Revision(
        uuid=revision_uuid,
        last_updated=timestamp,
        attributes={"title": "Sample HTML Content"},
    )
    return HTMLContent(
        uuid=str(uuid.uuid4()),
        title="Sample HTML Content",
        created_by=users["editor"]["uuid"],
        created_at=timestamp,
        timestamps=timestamp,
        revisions=[revision],
        categories=[],
    )


def seed_example_contents(users):
    """Return example content objects for each supported type."""
    timestamp = "2025-06-08T12:00:00"
    contents = []
    for ct in ContentType:
        for _ in range(2):
            rev_attrs = {"title": f"Example {ct.value}"}
            if ct is ContentType.PDF:
                rev_attrs["file_uuid"] = str(uuid.uuid4())
            rev = Revision(
                uuid=str(uuid.uuid4()),
                last_updated=timestamp,
                attributes=rev_attrs,
            )
            base_kwargs = dict(
                uuid=str(uuid.uuid4()),
                title=f"Example {ct.value}",
                created_by=users["editor"]["uuid"],
                created_at=timestamp,
                timestamps=timestamp,
                revisions=[rev],
                categories=[],
            )
            if ct is ContentType.HTML:
                contents.append(HTMLContent(**base_kwargs))
            elif ct is ContentType.PDF:
                contents.append(PDFContent(**base_kwargs))
            elif ct is ContentType.OFFICE_ADDRESS:
                contents.append(OfficeAddressContent(**base_kwargs))
            elif ct is ContentType.EVENT_SCHEDULE:
                contents.append(EventScheduleContent(**base_kwargs))
    return contents
