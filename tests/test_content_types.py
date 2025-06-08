import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from cms.types import ContentType


def test_supported_content_types():
    expected = {"html", "pdf", "office address", "event schedilw"}
    assert len(ContentType) == 4
    assert {item.value for item in ContentType} == expected
