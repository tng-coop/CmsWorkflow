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
