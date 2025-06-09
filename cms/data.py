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
        attributes={"title": "Sample HTML Content", "html_content": "<p>Sample HTML Content</p>"},
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
            if ct is ContentType.HTML:
                rev_attrs["html_content"] = f"<p>Example {ct.value}</p>"
            if ct is ContentType.PDF:
                # include a file UUID for seeded PDF content
                rev_attrs["file_uuid"] = str(uuid.uuid4())
            if ct is ContentType.OFFICE_ADDRESS:
                rev_attrs.update(
                    {
                        "postal_code": "00000",
                        "address": "123 Example Rd.",
                        "phone": "555-0000",
                        "fax": "555-0001",
                        "email": "info@example.com",
                    }
                )
            if ct is ContentType.EVENT_SCHEDULE:
                rev_attrs.update(
                    {
                        "start": "2025-06-08T09:00:00",
                        "end": "2025-06-08T10:00:00",
                        "all_day": False,
                    }
                )
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
