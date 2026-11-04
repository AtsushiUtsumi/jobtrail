from collections.abc import Sequence
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from jobtrail.domain.company.company import Company
from jobtrail.domain.company.company_source import CompanySource, SourceType
from jobtrail.domain.shared.ids import CompanyId, CompanySourceId


class CompanyState(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"
    ALL = "all"


class CompanyRepository(Protocol):
    def add(self, company: Company) -> None: ...

    def get(self, company_id: CompanyId) -> Company | None: ...

    def find_duplicate(
        self,
        normalized_name: str,
        normalized_url: str | None,
        exclude_id: CompanyId | None = None,
    ) -> Company | None: ...

    def search(
        self,
        query: str | None,
        min_priority: int | None,
        state: CompanyState,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Company], int]: ...


class CompanySourceRepository(Protocol):
    def add(self, source: CompanySource) -> None: ...

    def get(self, source_id: CompanySourceId) -> CompanySource | None: ...

    def latest(self, company_id: CompanyId, url: str) -> CompanySource | None: ...

    def list_for_company(
        self,
        company_id: CompanyId,
        source_type: SourceType | None,
        latest_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[CompanySource], int]: ...

    def find_stale(
        self, fetched_before: datetime, limit: int, offset: int
    ) -> tuple[Sequence[CompanySource], int]: ...
