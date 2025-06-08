from enum import Enum

class ContentType(str, Enum):
    """Enumerate supported content types."""

    HTML = "html"
    PDF = "pdf"
    OFFICE_ADDRESS = "office address"
    EVENT_SCHEDULE = "event schedule"
