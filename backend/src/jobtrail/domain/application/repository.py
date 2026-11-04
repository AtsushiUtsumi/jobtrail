from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from jobtrail.domain.application.application import Application
from jobtrail.domain.application.job_posting import JobPostingSnapshot
from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import ApplicationChannel, Outcome
from jobtrail.domain.shared.ids import (
    ApplicationId,
    CompanyId,
    DocumentVersionId,
    JobPostingId,
    StageId,
)


@dataclass(frozen=True)
class StageRow:
    id: StageId
    type: StageType
    label: str | None
    result: StageResult
    scheduled_at: datetime | None
    created_at: datetime
    result_recorded_at: datetime | None


@dataclass(frozen=True)
class ApplicationRow:
    """集約を経由しない読み取り専用の行（一覧・分析用）。"""

    id: ApplicationId
    company_id: CompanyId
    company_name: str
    position: str
    channel: ApplicationChannel
    applied_at: datetime | None
    outcome: Outcome
    submitted_document_version_id: DocumentVersionId | None
    created_at: datetime
    updated_at: datetime
    version: int
    stages: tuple[StageRow, ...]


class ApplicationRepository(Protocol):
    def add(self, application: Application) -> None: ...

    def get(self, application_id: ApplicationId) -> Application | None: ...


class ApplicationReadRepository(Protocol):
    def rows(self) -> Sequence[ApplicationRow]:
        """削除済み企業を除いた全応募を返す。"""
        ...


class JobPostingRepository(Protocol):
    def add(self, posting: JobPostingSnapshot) -> None: ...

    def get(self, posting_id: JobPostingId) -> JobPostingSnapshot | None: ...

    def latest(self, application_id: ApplicationId) -> JobPostingSnapshot | None: ...

    def list_for_application(
        self, application_id: ApplicationId
    ) -> Sequence[JobPostingSnapshot]: ...
