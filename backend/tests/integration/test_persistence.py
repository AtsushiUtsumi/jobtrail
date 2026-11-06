"""実 PostgreSQL でのみ確認できる性質（並行更新、制約、JSON の往復）。"""

import threading
from uuid import UUID

import pytest
import sqlalchemy as sa

from jobtrail.domain.company.company import Company
from jobtrail.domain.shared.errors import ConflictError, DuplicateCompanyError
from jobtrail.infra.db.models import company_sources, job_postings
from jobtrail.schemas.application import UpdateApplicationInput
from jobtrail.schemas.skill_profile import AddSkillInput
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.skill_profile import commands as profile
from tests.usecase.helpers import NOW, new_application


def test_lost_update_is_detected_between_two_sessions(ctx: AppContext) -> None:
    target = new_application(ctx)
    with ctx.uow_factory() as first, ctx.uow_factory() as second:
        one = first.applications.get(target.id)
        two = second.applications.get(target.id)
        assert one is not None and two is not None
        one.update_details(NOW, memo="先")
        two.update_details(NOW, memo="後")
        first.commit()
        with pytest.raises(ConflictError):
            second.commit()
    fetched = application.update_application(
        ctx, UpdateApplicationInput(application_id=target.id, position="SRE")
    )
    assert fetched.memo == "先"


def test_concurrent_updates_with_same_expected_version_let_one_win(ctx: AppContext) -> None:
    target = new_application(ctx)
    barrier = threading.Barrier(5)
    results: list[str] = []

    def worker(index: int) -> None:
        barrier.wait()
        try:
            application.update_application(
                ctx,
                UpdateApplicationInput(
                    application_id=target.id, memo=str(index), expected_version=target.version
                ),
            )
            results.append("ok")
        except ConflictError:
            results.append("conflict")

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert results.count("ok") == 1
    assert results.count("conflict") == 4


def test_unique_index_catches_duplicates_that_pass_the_check(ctx: AppContext) -> None:
    with ctx.uow_factory() as uow:
        uow.companies.add(Company.register("アクメ", None, "", NOW))
        uow.commit()
    with ctx.uow_factory() as uow, pytest.raises(DuplicateCompanyError):
        uow.companies.add(Company.register("株式会社アクメ", None, "", NOW))
        uow.commit()


def test_profile_save_detects_stale_version(ctx: AppContext) -> None:
    profile.add_skill(ctx, AddSkillInput(name="Go"))
    with ctx.uow_factory() as uow:
        stale = uow.skill_profile.get()
        uow.commit()
    profile.add_skill(ctx, AddSkillInput(name="Rust"))
    with ctx.uow_factory() as uow, pytest.raises(ConflictError):
        uow.skill_profile.save(stale)


def test_schema_uses_timestamptz_and_jsonb(ctx: AppContext, database_url: str) -> None:
    engine = sa.create_engine(database_url)
    columns = {
        (table, column["name"]): column["type"]
        for table in (company_sources.name, job_postings.name)
        for column in sa.inspect(engine).get_columns(table)
    }
    engine.dispose()
    assert str(columns[("company_sources", "extracted_fields")]) == "JSONB"
    assert columns[("company_sources", "fetched_at")].timezone is True
    assert str(columns[("company_sources", "id")]) == "UUID"


def test_uuid_keys_are_native(ctx: AppContext) -> None:
    assert isinstance(new_application(ctx).id, UUID)
