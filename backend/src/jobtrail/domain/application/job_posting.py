from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from jobtrail.domain.application.value_objects import SalaryRange
from jobtrail.domain.company.company_source import AcquiredBy
from jobtrail.domain.shared.ids import ApplicationId, JobPostingId, new_id
from jobtrail.domain.shared.value_objects import content_hash


@dataclass(eq=False)
class JobPostingSnapshot:
    """求人票の 1 版。追記のみで、更新できるのは解釈である summary だけ。"""

    id: JobPostingId
    application_id: ApplicationId
    url: str | None
    fetched_at: datetime
    content_hash: str
    raw_text: str
    summary: str
    salary_range: SalaryRange | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_policy: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    required: list[str] = field(default_factory=list)
    preferred: list[str] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)
    acquired_by: AcquiredBy = AcquiredBy.USER_PASTE
    revision: int = 1

    @classmethod
    def capture(
        cls,
        application_id: ApplicationId,
        url: str | None,
        raw_text: str,
        fetched_at: datetime,
        previous: "JobPostingSnapshot | None",
        **attributes: Any,
    ) -> "JobPostingSnapshot":
        return cls(
            id=new_id(),
            application_id=application_id,
            url=url,
            fetched_at=fetched_at,
            content_hash=content_hash(raw_text),
            raw_text=raw_text,
            revision=previous.revision + 1 if previous else 1,
            **attributes,
        )

    def is_same_content(self, raw_text: str) -> bool:
        return self.content_hash == content_hash(raw_text)

    def update_summary(self, summary: str) -> None:
        self.summary = summary
