import pytest

from jobtrail.domain.company.company_source import AcquiredBy, SaveResult, SourceType
from jobtrail.domain.company.repository import CompanyState
from jobtrail.domain.shared.errors import (
    ConflictError,
    ContentTooLargeError,
    DomainError,
    DuplicateCompanyError,
    NotFoundError,
)
from jobtrail.schemas.company import (
    CompanyVersionInput,
    FindCompaniesInput,
    FindStaleCompanySourcesInput,
    GetCompanyInput,
    GetCompanySourceInput,
    GetCompanySourcesInput,
    RegisterCompanyInput,
    SaveCompanySourceInput,
    UpdateCompanyInput,
    UpdateCompanySourceSummaryInput,
)
from jobtrail.usecase.company import commands as company
from jobtrail.usecase.context import AppContext


def register(ctx: AppContext, name: str = "株式会社アクメ", url: str | None = None):  # type: ignore[no-untyped-def]
    return company.register_company(ctx, RegisterCompanyInput(name=name, url=url))


def save(ctx: AppContext, company_id, raw_text: str = "本文", **values):  # type: ignore[no-untyped-def]
    base = {
        "company_id": company_id,
        "source_type": SourceType.ABOUT,
        "url": "https://acme.example/about",
        "raw_text": raw_text,
        **values,
    }
    return company.save_company_source(ctx, SaveCompanySourceInput(**base))


def test_duplicate_name_returns_existing_id(ctx: AppContext) -> None:
    existing = register(ctx)
    with pytest.raises(DuplicateCompanyError) as info:
        register(ctx, "アクメ")
    assert info.value.details["existing_id"] == str(existing.id)


def test_duplicate_url_is_rejected(ctx: AppContext) -> None:
    register(ctx, "A社", "https://acme.example/")
    with pytest.raises(DuplicateCompanyError):
        register(ctx, "B社", "https://ACME.example")


def test_deleted_company_does_not_block_registration(ctx: AppContext) -> None:
    existing = register(ctx)
    company.delete_company(ctx, CompanyVersionInput(company_id=existing.id))
    register(ctx)


def test_restore_is_blocked_by_new_duplicate(ctx: AppContext) -> None:
    existing = register(ctx)
    company.delete_company(ctx, CompanyVersionInput(company_id=existing.id))
    register(ctx)
    with pytest.raises(DuplicateCompanyError):
        company.restore_company(ctx, CompanyVersionInput(company_id=existing.id))


def test_rename_to_existing_company_is_rejected(ctx: AppContext) -> None:
    register(ctx, "A社")
    other = register(ctx, "B社")
    with pytest.raises(DuplicateCompanyError):
        company.update_company(ctx, UpdateCompanyInput(company_id=other.id, name="A社"))


def test_update_is_partial_and_can_clear_nullable(ctx: AppContext) -> None:
    created = company.register_company(
        ctx, RegisterCompanyInput(name="A社", url="https://a.example", priority=3, memo="m")
    )
    updated = company.update_company(
        ctx, UpdateCompanyInput(company_id=created.id, url=None, memo=None)
    )
    assert (updated.name, updated.url, updated.priority, updated.memo) == ("A社", None, 3, "m")
    assert updated.version == created.version + 1


def test_expected_version_is_verified_when_given(ctx: AppContext) -> None:
    created = register(ctx)
    company.update_company(ctx, UpdateCompanyInput(company_id=created.id, memo="a"))
    with pytest.raises(ConflictError):
        company.update_company(
            ctx,
            UpdateCompanyInput(company_id=created.id, memo="b", expected_version=created.version),
        )


def test_find_filters_by_name_priority_and_state(ctx: AppContext) -> None:
    company.register_company(ctx, RegisterCompanyInput(name="株式会社アクメ", priority=5))
    low = company.register_company(ctx, RegisterCompanyInput(name="ベータ", priority=1))
    deleted = register(ctx, "ガンマ")
    company.delete_company(ctx, CompanyVersionInput(company_id=deleted.id))

    assert company.find_companies(ctx, FindCompaniesInput(query="アクメ")).total == 1
    assert company.find_companies(ctx, FindCompaniesInput(query="100%")).total == 0
    assert company.find_companies(ctx, FindCompaniesInput(min_priority=3)).total == 1
    assert company.find_companies(ctx, FindCompaniesInput()).total == 2
    assert company.find_companies(ctx, FindCompaniesInput(state=CompanyState.ALL)).total == 3
    only_deleted = company.find_companies(ctx, FindCompaniesInput(state=CompanyState.DELETED))
    assert [c.id for c in only_deleted.items] == [deleted.id]
    paged = company.find_companies(ctx, FindCompaniesInput(limit=1, offset=1))
    assert (len(paged.items), paged.total) == (1, 2)
    assert paged.items[0].id == low.id


def test_deleted_company_can_still_be_fetched(ctx: AppContext) -> None:
    created = register(ctx)
    company.delete_company(ctx, CompanyVersionInput(company_id=created.id))
    fetched = company.get_company(ctx, GetCompanyInput(company_id=created.id))
    assert fetched.deleted_at is not None


def test_source_is_versioned_by_content(ctx: AppContext) -> None:
    created = register(ctx)
    first = save(ctx, created.id)
    same = save(ctx, created.id)
    changed = save(ctx, created.id, "新しい本文", summary="要約")

    assert first.result is SaveResult.CREATED
    assert same.result is SaveResult.UNCHANGED
    assert same.source.id == first.source.id
    assert same.source.fetched_at >= first.source.fetched_at
    assert changed.result is SaveResult.NEW_REVISION
    assert changed.source.revision == 2

    latest = company.get_company_sources(ctx, GetCompanySourcesInput(company_id=created.id))
    assert [s.revision for s in latest.items] == [2]
    every = company.get_company_sources(
        ctx, GetCompanySourcesInput(company_id=created.id, latest_only=False)
    )
    assert every.total == 2
    old = company.get_company_source(ctx, GetCompanySourceInput(source_id=first.source.id))
    assert old.raw_text == "本文"


def test_url_variants_share_revisions(ctx: AppContext) -> None:
    created = register(ctx)
    save(ctx, created.id)
    result = save(ctx, created.id, url="https://ACME.example/about/")
    assert result.result is SaveResult.UNCHANGED


def test_oversized_source_is_rejected(ctx: AppContext) -> None:
    created = register(ctx)
    limit = ctx.settings.max_raw_text_chars
    with pytest.raises(ContentTooLargeError):
        save(ctx, created.id, "あ" * (limit + 1))
    assert save(ctx, created.id, "あ" * limit).result is SaveResult.CREATED


def test_source_for_deleted_company_is_rejected(ctx: AppContext) -> None:
    created = register(ctx)
    company.delete_company(ctx, CompanyVersionInput(company_id=created.id))
    with pytest.raises(DomainError) as info:
        save(ctx, created.id)
    assert info.value.code == "COMPANY_DELETED"


def test_summary_can_be_rewritten_without_touching_text(ctx: AppContext) -> None:
    created = register(ctx)
    saved = save(ctx, created.id, acquired_by=AcquiredBy.USER_PASTE)
    company.update_company_source_summary(
        ctx, UpdateCompanySourceSummaryInput(source_id=saved.source.id, summary="再要約")
    )
    detail = company.get_company_source(ctx, GetCompanySourceInput(source_id=saved.source.id))
    assert (detail.summary, detail.raw_text) == ("再要約", "本文")
    assert detail.acquired_by is AcquiredBy.USER_PASTE


def test_stale_sources_only_consider_latest_revision_of_active_companies(ctx: AppContext) -> None:
    created = register(ctx)
    save(ctx, created.id)
    save(ctx, created.id, "更新")
    stale = company.find_stale_company_sources(ctx, FindStaleCompanySourcesInput(older_than_days=0))
    assert [s.revision for s in stale.items] == [2]
    assert company.find_stale_company_sources(ctx, FindStaleCompanySourcesInput()).total == 0
    company.delete_company(ctx, CompanyVersionInput(company_id=created.id))
    deleted = company.find_stale_company_sources(
        ctx, FindStaleCompanySourcesInput(older_than_days=0)
    )
    assert deleted.total == 0


def test_missing_company_is_not_found_with_hint(ctx: AppContext) -> None:
    from uuid import uuid4

    with pytest.raises(NotFoundError) as info:
        company.get_company(ctx, GetCompanyInput(company_id=uuid4()))
    assert "find_companies" in info.value.hint
