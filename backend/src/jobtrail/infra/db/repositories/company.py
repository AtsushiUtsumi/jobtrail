from collections.abc import Sequence
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from jobtrail.domain.company.company import Company
from jobtrail.domain.company.company_source import CompanySource, SourceType
from jobtrail.domain.company.repository import CompanyState
from jobtrail.domain.shared.ids import CompanyId, CompanySourceId
from jobtrail.domain.shared.value_objects import normalize_company_name
from jobtrail.infra.db.errors import translate_integrity_error
from jobtrail.infra.db.models import companies, company_sources


class SqlCompanyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, company: Company) -> None:
        # 集約間に relationship が無いので、参照する側より先に INSERT されるよう確定する。
        self._session.add(company)
        try:
            self._session.flush()
        except IntegrityError as error:
            raise translate_integrity_error(error) from error

    def get(self, company_id: CompanyId) -> Company | None:
        return self._session.get(Company, company_id)

    def find_duplicate(
        self,
        normalized_name: str,
        normalized_url: str | None,
        exclude_id: CompanyId | None = None,
    ) -> Company | None:
        conditions = [companies.c.normalized_name == normalized_name]
        if normalized_url:
            conditions.append(companies.c.normalized_url == normalized_url)
        query = sa.select(Company).where(companies.c.deleted_at.is_(None), sa.or_(*conditions))
        if exclude_id is not None:
            query = query.where(companies.c.id != exclude_id)
        with self._session.no_autoflush:
            return self._session.scalars(query.limit(1)).first()

    def search(
        self,
        query: str | None,
        min_priority: int | None,
        state: CompanyState,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[Company], int]:
        conditions: list[sa.ColumnElement[bool]] = []
        if query:
            conditions.append(
                sa.or_(
                    companies.c.name.icontains(query, autoescape=True),
                    companies.c.normalized_name.contains(
                        normalize_company_name(query), autoescape=True
                    ),
                )
            )
        if min_priority is not None:
            conditions.append(companies.c.priority >= min_priority)
        if state is CompanyState.ACTIVE:
            conditions.append(companies.c.deleted_at.is_(None))
        elif state is CompanyState.DELETED:
            conditions.append(companies.c.deleted_at.is_not(None))
        total = self._session.scalar(
            sa.select(sa.func.count()).select_from(companies).where(*conditions)
        )
        items = self._session.scalars(
            sa.select(Company)
            .where(*conditions)
            .order_by(companies.c.priority.desc().nulls_last(), companies.c.updated_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return items, total or 0


class SqlCompanySourceRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, source: CompanySource) -> None:
        self._session.add(source)

    def get(self, source_id: CompanySourceId) -> CompanySource | None:
        return self._session.get(CompanySource, source_id)

    def latest(self, company_id: CompanyId, url: str) -> CompanySource | None:
        return self._session.scalars(
            sa.select(CompanySource)
            .where(company_sources.c.company_id == company_id, company_sources.c.url == url)
            .order_by(company_sources.c.revision.desc())
            .limit(1)
        ).first()

    def list_for_company(
        self,
        company_id: CompanyId,
        source_type: SourceType | None,
        latest_only: bool,
        limit: int,
        offset: int,
    ) -> tuple[Sequence[CompanySource], int]:
        conditions: list[sa.ColumnElement[bool]] = [company_sources.c.company_id == company_id]
        if source_type is not None:
            conditions.append(company_sources.c.source_type == source_type)
        if latest_only:
            conditions.append(self._is_latest())
        return self._page(conditions, limit, offset)

    def find_stale(
        self, fetched_before: datetime, limit: int, offset: int
    ) -> tuple[Sequence[CompanySource], int]:
        active = sa.select(companies.c.id).where(companies.c.deleted_at.is_(None))
        conditions = [
            self._is_latest(),
            company_sources.c.fetched_at < fetched_before,
            company_sources.c.company_id.in_(active),
        ]
        return self._page(conditions, limit, offset, oldest_first=True)

    def _is_latest(self) -> sa.ColumnElement[bool]:
        newer = company_sources.alias("newer")
        return ~sa.exists().where(
            newer.c.company_id == company_sources.c.company_id,
            newer.c.url == company_sources.c.url,
            newer.c.revision > company_sources.c.revision,
        )

    def _page(
        self,
        conditions: list[sa.ColumnElement[bool]],
        limit: int,
        offset: int,
        oldest_first: bool = False,
    ) -> tuple[Sequence[CompanySource], int]:
        total = self._session.scalar(
            sa.select(sa.func.count()).select_from(company_sources).where(*conditions)
        )
        fetched_at = company_sources.c.fetched_at
        items = self._session.scalars(
            sa.select(CompanySource)
            .where(*conditions)
            .order_by(fetched_at.asc() if oldest_first else fetched_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return items, total or 0
