from .types import ContentType
from .models import (
    HTMLContent,
    PDFContent,
    OfficeAddressContent,
    EventScheduleContent,
    Revision,
)


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
        categories=[],
    )


def seed_example_contents(users):
    """Return example content objects for each supported type."""
    timestamp = "2025-06-08T12:00:00"
    contents = []
    for ct in ContentType:
        for i in range(2):
            rev = Revision(
                uuid=f"{ct.value}-{i}-rev",
                last_updated=timestamp,
                attributes={"title": f"Example {ct.value} {i}"},
            )
            base_kwargs = dict(
                uuid=f"{ct.value}-{i}",
                title=f"Example {ct.value} {i}",
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
