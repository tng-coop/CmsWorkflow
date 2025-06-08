def check_required_metadata(content):
    """Ensure content contains required metadata fields."""
    required_fields = ["created_by", "created_at", "timestamps"]
    for field in required_fields:
        if field not in content["metadata"] or content["metadata"][field] is None:
            raise KeyError(f"Missing required metadata field: {field}")
