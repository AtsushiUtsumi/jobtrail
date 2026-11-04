from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from types import TracebackType
from typing import Any, Protocol, Self

from pydantic import BaseModel

from jobtrail.config import Settings
from jobtrail.domain.application.repository import (
    ApplicationReadRepository,
    ApplicationRepository,
    JobPostingRepository,
)
from jobtrail.domain.company.repository import CompanyRepository, CompanySourceRepository
from jobtrail.domain.document.repository import DocumentRepository
from jobtrail.domain.skill_profile.repository import (
    SkillProfileRepository,
    SubmissionRepository,
)


class UnitOfWork(Protocol):
    """トランザクション境界。commit しないまま抜けると変更は破棄される。"""

    companies: CompanyRepository
    company_sources: CompanySourceRepository
    applications: ApplicationRepository
    application_reads: ApplicationReadRepository
    job_postings: JobPostingRepository
    documents: DocumentRepository
    skill_profile: SkillProfileRepository
    submissions: SubmissionRepository

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...

    def check_connection(self) -> None: ...


def utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AppContext:
    uow_factory: Callable[[], UnitOfWork]
    settings: Settings
    now: Callable[[], datetime] = utc_now


def changes_of(
    data: BaseModel, *exclude: str, nullable: frozenset[str] = frozenset()
) -> dict[str, Any]:
    """指定された項目だけを取り出す。null は nullable の項目でのみクリアとして扱う。"""
    excluded = {*exclude, "expected_version"}
    return {
        name: value
        for name, value in data.model_dump(exclude_unset=True, exclude=excluded).items()
        if value is not None or name in nullable
    }
