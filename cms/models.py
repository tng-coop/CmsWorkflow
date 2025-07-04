from dataclasses import dataclass, field, asdict
from typing import List, Optional
from .types import ContentType

@dataclass
class Revision:
    uuid: str
    last_updated: str
    attributes: dict = field(default_factory=dict)


@dataclass
class Category:
    uuid: str
    name: str
    display_priority: int = 0
    archived: bool = False

@dataclass
class Content:
    uuid: str
    title: str
    type: ContentType = field(init=False)
    created_by: str
    created_at: str
    edited_by: Optional[str] = None
    edited_at: Optional[str] = None
    draft_requested_by: Optional[str] = None
    draft_requested_at: Optional[str] = None
    approved_by: Optional[str] = None
    approved_at: Optional[str] = None
    timestamps: str = ""
    revisions: List[Revision] = field(default_factory=list)
    published_revision: Optional[str] = None
    review_revision: Optional[str] = None
    categories: List[str] = field(default_factory=list)

    @property
    def review_requested(self) -> bool:
        """Return True when approval has been requested but not yet granted."""
        return self.draft_requested_by is not None and self.approved_at is None

    def to_dict(self):
        data = asdict(self)
        data["type"] = self.type.value
        data["review_requested"] = self.review_requested
        return data

@dataclass
class HTMLContent(Content):
    type: ContentType = field(default=ContentType.HTML, init=False)

@dataclass
class PDFContent(Content):
    type: ContentType = field(default=ContentType.PDF, init=False)

@dataclass
class OfficeAddressContent(Content):
    type: ContentType = field(default=ContentType.OFFICE_ADDRESS, init=False)

@dataclass
class EventScheduleContent(Content):
    type: ContentType = field(default=ContentType.EVENT_SCHEDULE, init=False)
