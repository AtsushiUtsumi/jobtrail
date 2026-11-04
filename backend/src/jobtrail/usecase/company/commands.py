from datetime import timedelta
from uuid import UUID

from jobtrail.domain.company.company import Company
from jobtrail.domain.company.company_source import CompanySource, SaveResult
from jobtrail.domain.shared.errors import (
    DomainError,
    DuplicateCompanyError,
    NotFoundError,
    check_version,
)
from jobtrail.domain.shared.value_objects import ensure_text_size, normalize_url
from jobtrail.schemas.common import Page
from jobtrail.schemas.company import (
    CompanyOutput,
    CompanySourceDetail,
    CompanySourceOutput,
    CompanyVersionInput,
    FindCompaniesInput,
    FindStaleCompanySourcesInput,
    GetCompanyInput,
    GetCompanySourceInput,
    GetCompanySourcesInput,
    RegisterCompanyInput,
    SaveCompanySourceInput,
    SaveCompanySourceOutput,
    UpdateCompanyInput,
    UpdateCompanySourceSummaryInput,
)
from jobtrail.usecase.context import AppContext, UnitOfWork, changes_of


def load_company(uow: UnitOfWork, company_id: UUID) -> Company:
    company = uow.companies.get(company_id)
    if company is None:
        raise NotFoundError("企業", company_id, "find_companies で ID を確認してください。")
    return company


def create_company(
    ctx: AppContext, uow: UnitOfWork, name: str, url: str | None, priority: int | None, memo: str
) -> Company:
    company = Company.register(name, url, priority, memo, ctx.now())
    _ensure_unique(uow, company)
    uow.companies.add(company)
    return company


def _ensure_unique(uow: UnitOfWork, company: Company) -> None:
    duplicate = uow.companies.find_duplicate(
        company.normalized_name, company.normalized_url, exclude_id=company.id
    )
    if duplicate is not None:
        raise DuplicateCompanyError(duplicate.id, duplicate.name)


def register_company(ctx: AppContext, data: RegisterCompanyInput) -> CompanyOutput:
    """企業を登録する。"""
    with ctx.uow_factory() as uow:
        company = create_company(ctx, uow, data.name, data.url, data.priority, data.memo)
        uow.commit()
        return CompanyOutput.model_validate(company)


def update_company(ctx: AppContext, data: UpdateCompanyInput) -> CompanyOutput:
    """企業の基本情報を部分更新する。"""
    with ctx.uow_factory() as uow:
        company = load_company(uow, data.company_id)
        check_version(company.version, data.expected_version)
        company.update(
            ctx.now(),
            **changes_of(data, "company_id", nullable=frozenset({"url", "priority"})),
        )
        _ensure_unique(uow, company)
        uow.commit()
        return CompanyOutput.model_validate(company)


def delete_company(ctx: AppContext, data: CompanyVersionInput) -> CompanyOutput:
    """企業を論理削除する。restore_company で復元できる。"""
    with ctx.uow_factory() as uow:
        company = load_company(uow, data.company_id)
        check_version(company.version, data.expected_version)
        company.delete(ctx.now())
        uow.commit()
        return CompanyOutput.model_validate(company)


def restore_company(ctx: AppContext, data: CompanyVersionInput) -> CompanyOutput:
    """論理削除した企業を復元する。"""
    with ctx.uow_factory() as uow:
        company = load_company(uow, data.company_id)
        check_version(company.version, data.expected_version)
        company.restore(ctx.now())
        _ensure_unique(uow, company)
        uow.commit()
        return CompanyOutput.model_validate(company)


def find_companies(ctx: AppContext, data: FindCompaniesInput) -> Page[CompanyOutput]:
    """社名・志望度・状態で企業を検索する。"""
    with ctx.uow_factory() as uow:
        items, total = uow.companies.search(
            data.query, data.min_priority, data.state, data.limit, data.offset
        )
        return Page(
            items=[CompanyOutput.model_validate(c) for c in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )


def get_company(ctx: AppContext, data: GetCompanyInput) -> CompanyOutput:
    """企業を 1 件取得する（論理削除済みも取得できる）。"""
    with ctx.uow_factory() as uow:
        return CompanyOutput.model_validate(load_company(uow, data.company_id))


def save_company_source(ctx: AppContext, data: SaveCompanySourceInput) -> SaveCompanySourceOutput:
    """企業情報のページを保存する。同じ URL の内容が変わっていれば新しい版として追記する。"""
    ensure_text_size(data.raw_text, ctx.settings.max_raw_text_chars)
    url = normalize_url(data.url)
    with ctx.uow_factory() as uow:
        company = load_company(uow, data.company_id)
        if company.is_deleted:
            raise DomainError(
                "COMPANY_DELETED",
                f"企業は削除済みです: {company.name}",
                "restore_company で復元してから保存してください。",
            )
        previous = uow.company_sources.latest(company.id, url)
        if previous is not None and previous.is_same_content(data.raw_text):
            previous.mark_refetched(ctx.now())
            uow.commit()
            return SaveCompanySourceOutput(
                result=SaveResult.UNCHANGED,
                source=CompanySourceOutput.model_validate(previous),
            )
        source = CompanySource.capture(
            company_id=company.id,
            source_type=data.source_type,
            url=url,
            raw_text=data.raw_text,
            summary=data.summary,
            extracted_fields=data.extracted_fields.model_dump(),
            acquired_by=data.acquired_by,
            fetched_at=ctx.now(),
            previous=previous,
        )
        uow.company_sources.add(source)
        uow.commit()
        return SaveCompanySourceOutput(
            result=SaveResult.NEW_REVISION if previous else SaveResult.CREATED,
            source=CompanySourceOutput.model_validate(source),
        )


def get_company_sources(ctx: AppContext, data: GetCompanySourcesInput) -> Page[CompanySourceOutput]:
    """企業の保存ページを本文なしで一覧する。既定では各 URL の最新版のみ。"""
    with ctx.uow_factory() as uow:
        load_company(uow, data.company_id)
        items, total = uow.company_sources.list_for_company(
            data.company_id, data.source_type, data.latest_only, data.limit, data.offset
        )
        return Page(
            items=[CompanySourceOutput.model_validate(s) for s in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )


def get_company_source(ctx: AppContext, data: GetCompanySourceInput) -> CompanySourceDetail:
    """保存ページを本文つきで取得する。"""
    with ctx.uow_factory() as uow:
        return CompanySourceDetail.model_validate(_load_source(uow, data.source_id))


def update_company_source_summary(
    ctx: AppContext, data: UpdateCompanySourceSummaryInput
) -> CompanySourceOutput:
    """保存ページの要約・抽出項目を更新する。本文は変更できない。"""
    with ctx.uow_factory() as uow:
        source = _load_source(uow, data.source_id)
        fields = data.extracted_fields.model_dump() if data.extracted_fields else None
        source.update_summary(data.summary, fields)
        uow.commit()
        return CompanySourceOutput.model_validate(source)


def find_stale_company_sources(
    ctx: AppContext, data: FindStaleCompanySourcesInput
) -> Page[CompanySourceOutput]:
    """取得から一定日数が経過した保存ページ（各 URL の最新版）を探す。"""
    days = data.older_than_days
    if days is None:
        days = ctx.settings.stale_source_days
    with ctx.uow_factory() as uow:
        items, total = uow.company_sources.find_stale(
            ctx.now() - timedelta(days=days), data.limit, data.offset
        )
        return Page(
            items=[CompanySourceOutput.model_validate(s) for s in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )


def _load_source(uow: UnitOfWork, source_id: UUID) -> CompanySource:
    source = uow.company_sources.get(source_id)
    if source is None:
        raise NotFoundError(
            "保存ページ", source_id, "get_company_sources で ID を確認してください。"
        )
    return source
