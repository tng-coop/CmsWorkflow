from .models import Content


def _get_metadata_value(content, field):
    if isinstance(content, Content):
        return getattr(content, field, None)
    if field in content:
        return content.get(field)
    return content.get("metadata", {}).get(field)


def check_required_metadata(content):
    """Ensure content contains required metadata fields."""
    required_fields = ["created_by", "created_at", "timestamps"]
    for field in required_fields:
        if _get_metadata_value(content, field) is None:
            raise KeyError(f"Missing required metadata field: {field}")


def request_approval(content, user, timestamp):
    """Mark the given content as awaiting admin approval."""
    if isinstance(content, Content):
        content.draft_requested_by = user["uuid"]
        content.draft_requested_at = timestamp
    else:
        if "draft_requested_by" in content or "metadata" not in content:
            content["draft_requested_by"] = user["uuid"]
            content["draft_requested_at"] = timestamp
        else:
            content.setdefault("metadata", {})
            content["metadata"]["draft_requested_by"] = user["uuid"]
            content["metadata"]["draft_requested_at"] = timestamp
    return content


def pending_approvals(contents):
    """Return items that are awaiting admin approval."""
    result = []
    for item in contents:
        if isinstance(item, Content):
            awaiting = (
                item.draft_requested_by is not None
                and item.approved_at is None
                and not item.archived
            )
        else:
            awaiting = (
                item.get("draft_requested_by") is not None
                and item.get("approved_at") is None
                and not item.get("archived")
            )
        if awaiting:
            result.append(item)
    return result


def start_draft(content, user, timestamp):
    """Begin editing a content item in Draft state.

    If another user already has the item in Draft status, raise a
    PermissionError indicating who is editing it.
    """
    if isinstance(content, Content):
        current_editor = content.edited_by
        if current_editor is not None and current_editor != user["uuid"]:
            raise PermissionError(f"User {current_editor} has it in draft status")
        content.edited_by = user["uuid"]
        content.edited_at = timestamp
    else:
        current_editor = content.get("edited_by")
        if current_editor is None and "metadata" in content:
            current_editor = content["metadata"].get("edited_by")
        if current_editor is not None and current_editor != user["uuid"]:
            raise PermissionError(f"User {current_editor} has it in draft status")
        if "edited_by" in content or "metadata" not in content:
            content["edited_by"] = user["uuid"]
            content["edited_at"] = timestamp
        else:
            content["metadata"]["edited_by"] = user["uuid"]
            content["metadata"]["edited_at"] = timestamp
    return content


def archive_content(content):
    """Mark a content item as archived."""
    if isinstance(content, Content):
        content.archived = True
    else:
        content["archived"] = True
    return content


def approve_content(content, user, timestamp):
    """Mark a content item as published/approved."""
    if isinstance(content, Content):
        content.approved_by = user["uuid"]
        content.approved_at = timestamp
        if content.review_revision is not None:
            content.published_revision = content.review_revision
        elif content.revisions:
            content.published_revision = content.revisions[-1].uuid
        content.pre_submission = False
        if content.review_content:
            content.published_content = content.review_content
            content.review_content = {}
    else:
        if "approved_by" in content or "metadata" not in content:
            content["approved_by"] = user["uuid"]
            content["approved_at"] = timestamp
        else:
            content.setdefault("metadata", {})
            content["metadata"]["approved_by"] = user["uuid"]
            content["metadata"]["approved_at"] = timestamp
        if content.get("review_revision"):
            content["published_revision"] = content.get("review_revision")
        elif content.get("revisions"):
            content["published_revision"] = content["revisions"][-1]["uuid"]
        content["pre_submission"] = False
        if content.get("review_content"):
            content["published_content"] = content.get("review_content")
            content["review_content"] = {}
    return content
