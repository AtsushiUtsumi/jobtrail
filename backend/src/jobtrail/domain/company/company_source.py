from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

from jobtrail.domain.shared.ids import CompanyId, CompanySourceId, new_id
from jobtrail.domain.shared.value_objects import content_hash


class SourceType(StrEnum):
    RECRUIT = "recruit"
    ABOUT = "about"
    BLOG = "blog"
    NEWS = "news"
    REVIEW = "review"
    OTHER = "other"


class AcquiredBy(StrEnum):
    CLAUDE_FETCH = "claude_fetch"
    USER_PASTE = "user_paste"


class SaveResult(StrEnum):
    CREATED = "created"
    NEW_REVISION = "new_revision"
    UNCHANGED = "unchanged"


@dataclass(eq=False)
class CompanySource:
    """保存ページの 1 版。raw_text（事実）は不変で、summary（解釈）だけ更新できる。"""

    id: CompanySourceId
    company_id: CompanyId
    source_type: SourceType
    url: str
    fetched_at: datetime
    content_hash: str
    raw_text: str
    summary: str
    extracted_fields: dict[str, Any] = field(default_factory=dict)
    acquired_by: AcquiredBy = AcquiredBy.USER_PASTE
    revision: int = 1

    @classmethod
    def capture(
        cls,
        company_id: CompanyId,
        source_type: SourceType,
        url: str,
        raw_text: str,
        summary: str,
        extracted_fields: dict[str, Any],
        acquired_by: AcquiredBy,
        fetched_at: datetime,
        previous: "CompanySource | None",
    ) -> "CompanySource":
        return cls(
            id=new_id(),
            company_id=company_id,
            source_type=source_type,
            url=url,
            fetched_at=fetched_at,
            content_hash=content_hash(raw_text),
            raw_text=raw_text,
            summary=summary,
            extracted_fields=extracted_fields,
            acquired_by=acquired_by,
            revision=previous.revision + 1 if previous else 1,
        )

    def is_same_content(self, raw_text: str) -> bool:
        return self.content_hash == content_hash(raw_text)

    def mark_refetched(self, fetched_at: datetime) -> None:
        self.fetched_at = fetched_at

    def update_summary(self, summary: str, extracted_fields: dict[str, Any] | None) -> None:
        self.summary = summary
        if extracted_fields is not None:
            self.extracted_fields = extracted_fields
