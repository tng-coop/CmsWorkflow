import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.data import seed_users, seed_example_contents
from cms.types import ContentType


def test_seed_example_contents():
    users = seed_users()
    contents = seed_example_contents(users)
    # there should be at least two items for each type
    type_counts = {ct: 0 for ct in ContentType}
    uuids = set()
    for item in contents:
        assert item.type in ContentType
        type_counts[item.type] += 1
        uuids.add(item.uuid)
        # ensure dataclass to_dict works
        assert item.to_dict()["type"] == item.type.value
        if item.type is ContentType.PDF:
            for rev in item.revisions:
                assert "file_uuid" in rev.attributes and rev.attributes["file_uuid"]
    assert all(count >= 2 for count in type_counts.values())
    assert len(uuids) == len(contents)
