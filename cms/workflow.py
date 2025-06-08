def check_required_metadata(content):
    """Ensure content contains required metadata fields."""
    required_fields = ["created_by", "created_at", "timestamps"]
    for field in required_fields:
        if field not in content["metadata"] or content["metadata"][field] is None:
            raise KeyError(f"Missing required metadata field: {field}")


def request_approval(content, user, timestamp):
    """Mark the given content as awaiting admin approval."""
    content["metadata"]["draft_requested_by"] = user["uuid"]
    content["metadata"]["draft_requested_at"] = timestamp
    content["state"] = "AwaitingApproval"
    return content


def pending_approvals(contents):
    """Return items that are awaiting admin approval."""
    return [item for item in contents if item.get("state") == "AwaitingApproval"]


def start_draft(content, user, timestamp):
    """Begin editing a content item in Draft state.

    If another user already has the item in Draft status, raise a
    PermissionError indicating who is editing it.
    """
    current_editor = content["metadata"].get("edited_by")
    if (
        content.get("state") == "Draft"
        and current_editor is not None
        and current_editor != user["uuid"]
    ):
        raise PermissionError(f"User {current_editor} has it in draft status")

    content["metadata"]["edited_by"] = user["uuid"]
    content["metadata"]["edited_at"] = timestamp
    content["state"] = "Draft"
    return content


def archive_content(content):
    """Mark a content item as archived."""
    content["state"] = "Archived"
    content["archived"] = True
    return content
