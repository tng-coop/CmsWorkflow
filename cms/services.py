import uuid
from typing import Dict, List

from .types import ContentType

from .db_context import DbContext
from .workflow import (
    check_required_metadata,
    request_approval,
    start_draft,
    archive_content,
    approve_content,
    pending_approvals,
)


class CategoryService:
    def __init__(self, ctx: DbContext):
        self.ctx = ctx

    def list_categories(self) -> List[Dict]:
        def sort_key(cat):
            prio = cat.get("display_priority", 0)
            if prio and prio > 0:
                return (0, prio)
            return (1, cat.get("name", "").lower())

        categories = [c for c in self.ctx.categories.values() if not c.get("archived")]
        categories.sort(key=sort_key)
        return categories

    def get_category(self, uuid: str) -> Dict:
        return self.ctx.categories.get(uuid)

    def create_category(self, data: Dict) -> Dict:
        cat_uuid = data.get("uuid") or str(uuid.uuid4())
        category = {
            "uuid": cat_uuid,
            "name": data.get("name", ""),
            "display_priority": int(data.get("display_priority", 0)),
            "archived": False,
        }
        self.ctx.categories[cat_uuid] = category
        return category

    def update_category(self, uuid: str, data: Dict) -> Dict:
        existing = self.ctx.categories.get(uuid)
        if existing is None:
            return None
        updated = existing.copy()
        updated.update({
            "name": data.get("name", existing.get("name")),
            "display_priority": int(data.get("display_priority", existing.get("display_priority", 0))),
        })
        self.ctx.categories[uuid] = updated
        return updated

    def archive_category(self, uuid: str) -> Dict:
        cat = self.ctx.categories.get(uuid)
        if cat is not None:
            cat["archived"] = True
            self.ctx.categories[uuid] = cat
        return cat


class ContentService:
    def __init__(self, ctx: DbContext):
        self.ctx = ctx

    def _with_flags(self, item: Dict) -> Dict:
        result = item.copy()
        result["is_published"] = bool(result.get("published_revision"))
        result["review_requested"] = bool(result.get("draft_requested_by")) and not bool(result.get("approved_at"))
        return result

    def list_all(self, authenticated: bool) -> List[Dict]:
        return [
            self._with_flags(item)
            for item in self.ctx.contents.values()
            if authenticated or bool(item.get("published_revision"))
        ]

    def list_by_type(self, item_type: str, authenticated: bool) -> List[Dict]:
        return [
            self._with_flags(i)
            for i in self.ctx.contents.values()
            if i.get("type") == item_type
            and (authenticated or bool(i.get("published_revision")))
        ]

    def get(self, uuid: str) -> Dict:
        item = self.ctx.contents.get(uuid)
        return self._with_flags(item) if item else None

    # Internal helpers -------------------------------------------------
    @staticmethod
    def _ensure_revision_structure(item: Dict):
        if "revisions" not in item or not item["revisions"]:
            rev_uuid = str(uuid.uuid4())
            ts = item.get("timestamps") or item.get("metadata", {}).get("timestamps")
            attrs = {}
            if "title" in item:
                attrs["title"] = item["title"]
            if "file_uuid" in item:
                attrs["file_uuid"] = item.pop("file_uuid")
            if "html_content" in item:
                attrs["html_content"] = item.pop("html_content")
            if "postal_code" in item:
                attrs["postal_code"] = item.pop("postal_code")
            if "address" in item:
                attrs["address"] = item.pop("address")
            if "phone" in item:
                attrs["phone"] = item.pop("phone")
            if "fax" in item:
                attrs["fax"] = item.pop("fax")
            if "email" in item:
                attrs["email"] = item.pop("email")
            if "start" in item:
                attrs["start"] = item.pop("start")
            if "end" in item:
                attrs["end"] = item.pop("end")
            if "all_day" in item:
                attrs["all_day"] = item.pop("all_day")
            item["revisions"] = [{"uuid": rev_uuid, "last_updated": ts, "attributes": attrs}]
        else:
            for rev in item["revisions"]:
                rev.setdefault(
                    "last_updated", item.get("timestamps") or item.get("metadata", {}).get("timestamps")
                )

    @staticmethod
    def _add_revision(item: Dict):
        rev_uuid = str(uuid.uuid4())
        ts = (
            item.get("edited_at")
            or item.get("timestamps")
            or item.get("metadata", {}).get("edited_at")
            or item.get("metadata", {}).get("timestamps")
        )
        attrs = {}
        if "title" in item:
            attrs["title"] = item["title"]
        if "file_uuid" in item:
            attrs["file_uuid"] = item.pop("file_uuid")
        elif item.get("type") == ContentType.PDF.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "file_uuid" in last:
                attrs["file_uuid"] = last["file_uuid"]
        if "html_content" in item:
            attrs["html_content"] = item.pop("html_content")
        elif item.get("type") == ContentType.HTML.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "html_content" in last:
                attrs["html_content"] = last["html_content"]
        if "postal_code" in item:
            attrs["postal_code"] = item.pop("postal_code")
        elif item.get("type") == ContentType.OFFICE_ADDRESS.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "postal_code" in last:
                attrs["postal_code"] = last["postal_code"]
        if "address" in item:
            attrs["address"] = item.pop("address")
        elif item.get("type") == ContentType.OFFICE_ADDRESS.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "address" in last:
                attrs["address"] = last["address"]
        if "phone" in item:
            attrs["phone"] = item.pop("phone")
        elif item.get("type") == ContentType.OFFICE_ADDRESS.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "phone" in last:
                attrs["phone"] = last["phone"]
        if "fax" in item:
            attrs["fax"] = item.pop("fax")
        elif item.get("type") == ContentType.OFFICE_ADDRESS.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "fax" in last:
                attrs["fax"] = last["fax"]
        if "email" in item:
            attrs["email"] = item.pop("email")
        elif item.get("type") == ContentType.OFFICE_ADDRESS.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "email" in last:
                attrs["email"] = last["email"]
        if "start" in item:
            attrs["start"] = item.pop("start")
        elif item.get("type") == ContentType.EVENT_SCHEDULE.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "start" in last:
                attrs["start"] = last["start"]
        if "end" in item:
            attrs["end"] = item.pop("end")
        elif item.get("type") == ContentType.EVENT_SCHEDULE.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "end" in last:
                attrs["end"] = last["end"]
        if "all_day" in item:
            attrs["all_day"] = item.pop("all_day")
        elif item.get("type") == ContentType.EVENT_SCHEDULE.value and item.get("revisions"):
            last = item["revisions"][-1].get("attributes", {})
            if "all_day" in last:
                attrs["all_day"] = last["all_day"]
        item.setdefault("revisions", [])
        item["revisions"].append({"uuid": rev_uuid, "last_updated": ts, "attributes": attrs})
        item["review_revision"] = rev_uuid

    def create(self, item: Dict) -> Dict:
        item_uuid = item.get("uuid") or str(uuid.uuid4())
        item["uuid"] = item_uuid
        item.pop("state", None)
        self._ensure_revision_structure(item)
        self.ctx.contents[item_uuid] = item
        return self._with_flags(item)

    def update(self, uuid: str, incoming: Dict) -> Dict:
        existing = self.ctx.contents.get(uuid)
        if existing is None:
            return None
        new_type = incoming.get("type", existing.get("type"))
        if new_type != existing.get("type"):
            raise ValueError("type cannot be changed")

        metadata_fields = {
            "created_by",
            "created_at",
            "edited_by",
            "edited_at",
            "draft_requested_by",
            "draft_requested_at",
            "approved_by",
            "approved_at",
            "timestamps",
        }
        if incoming.get("metadata") is not None:
            if incoming.get("metadata") != existing.get("metadata"):
                raise ValueError("metadata immutable")
        else:
            for field in metadata_fields:
                if field in incoming and incoming[field] != existing.get(field):
                    raise ValueError("metadata immutable")

        updated = existing.copy()
        excluded = metadata_fields | {"type", "metadata", "uuid", "state"}
        updated.update({k: v for k, v in incoming.items() if k not in excluded})
        self._ensure_revision_structure(updated)
        self._add_revision(updated)
        self.ctx.contents[uuid] = updated
        return self._with_flags(updated)

    def archive(self, uuid: str) -> Dict:
        item = self.ctx.contents.get(uuid)
        if item is not None:
            archive_content(item)
            self.ctx.contents[uuid] = item
        return self._with_flags(item) if item else None

    def request_approval(self, uuid: str, data: Dict) -> Dict:
        item = self.ctx.contents.get(uuid)
        if item is None:
            return None
        self._ensure_revision_structure(item)
        request_approval(item, {"uuid": data.get("user_uuid")}, data.get("timestamp"))
        self.ctx.contents[uuid] = item
        return self._with_flags(item)

    def approve(self, uuid: str, data: Dict) -> Dict:
        item = self.ctx.contents.get(uuid)
        if item is None:
            return None
        self._ensure_revision_structure(item)
        approve_content(item, {"uuid": data.get("user_uuid")}, data.get("timestamp"))
        self.ctx.contents[uuid] = item
        return self._with_flags(item)

    def start_draft(self, uuid: str, data: Dict) -> Dict:
        item = self.ctx.contents.get(uuid)
        if item is None:
            return None
        self._ensure_revision_structure(item)
        start_draft(item, {"uuid": data.get("user_uuid")}, data.get("timestamp"))
        self.ctx.contents[uuid] = item
        return self._with_flags(item)

    def pending_approvals(self) -> List[Dict]:
        pending = pending_approvals(self.ctx.contents.values())
        return [self._with_flags(item) for item in pending]


class TokenService:
    def __init__(self, ctx: DbContext):
        self.ctx = ctx

    def create_token(self, username: str) -> str:
        token = f"token-{username}"
        self.ctx.tokens[token] = username
        return token

    def validate_token(self, token: str) -> bool:
        return token in self.ctx.tokens
