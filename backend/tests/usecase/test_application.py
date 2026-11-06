from datetime import timedelta
from uuid import UUID

import pytest
from pydantic import ValidationError

from jobtrail.domain.application.repository import ApplicationSort
from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import (
    ApplicationChannel,
    ApplicationStatus,
    Outcome,
)
from jobtrail.domain.company.company_source import SaveResult
from jobtrail.domain.shared.errors import (
    ConflictError,
    ContentTooLargeError,
    DomainError,
    DuplicateCompanyError,
)
from jobtrail.schemas.application import (
    AddApplicationInput,
    CloseApplicationInput,
    FindApplicationsInput,
    GetApplicationInput,
    GetJobPostingInput,
    GetJobPostingsInput,
    NewCompanyInput,
    RecordStageResultInput,
    ReopenApplicationInput,
    RescheduleStageInput,
    SalaryRangeSchema,
    SaveJobPostingInput,
    UpdateApplicationInput,
    UpdateJobPostingSummaryInput,
    UpdateStageMemoInput,
)
from jobtrail.schemas.company import CompanyVersionInput, RegisterCompanyInput
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.application import job_postings
from jobtrail.usecase.company import commands as company
from jobtrail.usecase.context import AppContext
from tests.usecase.helpers import NOW, applied, new_application, stage


def test_add_with_new_company_starts_as_considering(ctx: AppContext) -> None:
    created = new_application(ctx)
    assert created.status is ApplicationStatus.CONSIDERING
    assert created.company_name == "アクメ"


def test_add_with_existing_company(ctx: AppContext) -> None:
    existing = company.register_company(ctx, RegisterCompanyInput(name="アクメ"))
    created = application.add_application(
        ctx, AddApplicationInput(company_id=existing.id, position="SRE")
    )
    assert created.company_id == existing.id


def test_new_company_duplicate_returns_existing_id_and_creates_nothing(ctx: AppContext) -> None:
    existing = company.register_company(ctx, RegisterCompanyInput(name="アクメ"))
    with pytest.raises(DuplicateCompanyError) as info:
        new_application(ctx)
    assert info.value.details["existing_id"] == str(existing.id)
    assert application.find_applications(ctx, FindApplicationsInput()).total == 0


def test_add_requires_exactly_one_company_reference(ctx: AppContext) -> None:
    with pytest.raises(ValidationError):
        AddApplicationInput(position="SWE")
    existing = company.register_company(ctx, RegisterCompanyInput(name="アクメ"))
    with pytest.raises(ValidationError):
        AddApplicationInput(
            company_id=existing.id, new_company=NewCompanyInput(name="x"), position="SWE"
        )


def test_add_to_deleted_company_is_rejected(ctx: AppContext) -> None:
    existing = company.register_company(ctx, RegisterCompanyInput(name="アクメ"))
    company.delete_company(ctx, CompanyVersionInput(company_id=existing.id))
    with pytest.raises(DomainError) as info:
        application.add_application(
            ctx, AddApplicationInput(company_id=existing.id, position="SWE")
        )
    assert info.value.code == "COMPANY_DELETED"


def test_full_flow_to_offer(ctx: AppContext) -> None:
    target = applied(ctx)
    target = stage(ctx, target, StageType.DOCUMENT, StageResult.PASSED)
    assert target.status is ApplicationStatus.DOCUMENT
    target = stage(ctx, target, StageType.FIRST_INTERVIEW)
    assert target.status is ApplicationStatus.FIRST_INTERVIEW
    assert target.stage_type is StageType.FIRST_INTERVIEW
    target = application.record_stage_result(
        ctx,
        RecordStageResultInput(
            application_id=target.id,
            stage_id=target.stages[-1].id,
            result=StageResult.PASSED,
        ),
    )
    target = stage(ctx, target, StageType.OFFER, StageResult.PASSED)
    assert target.status is ApplicationStatus.OFFER
    target = application.close_application(
        ctx, CloseApplicationInput(application_id=target.id, outcome=Outcome.OFFER_ACCEPTED)
    )
    assert target.status is ApplicationStatus.OFFER_ACCEPTED
    assert target.outcome is Outcome.OFFER_ACCEPTED
    assert _positions(ctx, target.id) == [0, 1, 2]


def _positions(ctx: AppContext, application_id: UUID) -> list[int]:
    with ctx.uow_factory() as uow:
        loaded = uow.applications.get(application_id)
        assert loaded is not None
        return [s.position for s in loaded.stages]


def test_rejection_reopen_cycle_persists(ctx: AppContext) -> None:
    target = applied(ctx)
    target = stage(ctx, target, StageType.FIRST_INTERVIEW, StageResult.REJECTED)
    assert target.outcome is Outcome.REJECTED
    target = application.reopen_application(ctx, ReopenApplicationInput(application_id=target.id))
    assert target.status is ApplicationStatus.FIRST_INTERVIEW
    assert target.stages[-1].result is StageResult.PENDING


def test_stage_edits_persist_and_bump_version(ctx: AppContext) -> None:
    target = stage(ctx, applied(ctx), StageType.FIRST_INTERVIEW)
    stage_id = target.stages[0].id
    moved = application.reschedule_stage(
        ctx,
        RescheduleStageInput(application_id=target.id, stage_id=stage_id, scheduled_at=NOW),
    )
    noted = application.update_stage_memo(
        ctx, UpdateStageMemoInput(application_id=target.id, stage_id=stage_id, memo="質問")
    )
    assert moved.version == target.version + 1
    assert noted.version == target.version + 2
    fetched = application.get_application(ctx, GetApplicationInput(application_id=target.id))
    assert fetched.stages[0].scheduled_at == NOW
    assert fetched.stages[0].memo == "質問"


def test_stale_expected_version_is_conflict(ctx: AppContext) -> None:
    target = new_application(ctx)
    application.update_application(ctx, UpdateApplicationInput(application_id=target.id, memo="a"))
    with pytest.raises(ConflictError) as info:
        application.update_application(
            ctx,
            UpdateApplicationInput(
                application_id=target.id, memo="b", expected_version=target.version
            ),
        )
    assert info.value.details["current_version"] == target.version + 1


def test_update_is_partial(ctx: AppContext) -> None:
    target = new_application(ctx, agent_name="担当A")
    updated = application.update_application(
        ctx, UpdateApplicationInput(application_id=target.id, agent_name=None, position=None)
    )
    assert updated.agent_name is None
    assert updated.position == "SWE"


def test_find_filters(ctx: AppContext) -> None:
    first = applied(ctx, "アクメ", channel=ApplicationChannel.AGENT)
    second = new_application(ctx, "ベータ")
    find = application.find_applications

    assert find(ctx, FindApplicationsInput(statuses=[ApplicationStatus.DOCUMENT])).total == 1
    assert find(ctx, FindApplicationsInput(statuses=[ApplicationStatus.CONSIDERING])).total == 1
    both = [ApplicationStatus.DOCUMENT, ApplicationStatus.CONSIDERING]
    assert find(ctx, FindApplicationsInput(statuses=both)).total == 2
    assert find(ctx, FindApplicationsInput(statuses=[ApplicationStatus.OFFER])).total == 0
    assert find(ctx, FindApplicationsInput(channel=ApplicationChannel.AGENT)).total == 1
    assert find(ctx, FindApplicationsInput(company_id=second.company_id)).total == 1
    assert find(ctx, FindApplicationsInput(query="ベータ")).total == 1
    assert find(ctx, FindApplicationsInput(query="swe")).total == 2
    assert find(ctx, FindApplicationsInput(outcome=Outcome.REJECTED)).total == 0
    window = FindApplicationsInput(
        applied_from=NOW - timedelta(days=1), applied_to=NOW + timedelta(days=1)
    )
    assert [a.id for a in find(ctx, window).items] == [first.id]
    assert find(ctx, FindApplicationsInput(applied_from=NOW + timedelta(days=1))).total == 0
    paged = find(ctx, FindApplicationsInput(limit=1, offset=1))
    assert (len(paged.items), paged.total) == (1, 2)


def test_deleted_company_applications_are_hidden_from_lists(ctx: AppContext) -> None:
    target = new_application(ctx)
    company.delete_company(ctx, CompanyVersionInput(company_id=target.company_id))
    assert application.find_applications(ctx, FindApplicationsInput()).total == 0


def posting(ctx: AppContext, application_id, raw_text: str = "求人", **values):  # type: ignore[no-untyped-def]
    return job_postings.save_job_posting(
        ctx, SaveJobPostingInput(application_id=application_id, raw_text=raw_text, **values)
    )


def test_job_postings_are_append_only(ctx: AppContext) -> None:
    target = new_application(ctx)
    first = posting(
        ctx,
        target.id,
        salary_range=SalaryRangeSchema(minimum=6_000_000, maximum=9_000_000),
        tech_stack=["Python"],
    )
    same = posting(ctx, target.id)
    changed = posting(ctx, target.id, "求人（改訂）")

    assert first.result is SaveResult.CREATED
    assert same.result is SaveResult.UNCHANGED
    assert same.posting.fetched_at == first.posting.fetched_at
    assert changed.result is SaveResult.NEW_REVISION
    assert changed.posting.revision == 2

    listed = job_postings.get_job_postings(ctx, GetJobPostingsInput(application_id=target.id))
    assert [p.revision for p in listed.items] == [2, 1]
    detail = job_postings.get_job_posting(ctx, GetJobPostingInput(posting_id=first.posting.id))
    assert detail.raw_text == "求人"
    assert detail.salary_range is not None
    assert detail.salary_range.maximum == 9_000_000
    assert detail.tech_stack == ["Python"]


def test_job_posting_summary_update_keeps_text(ctx: AppContext) -> None:
    target = new_application(ctx)
    saved = posting(ctx, target.id)
    job_postings.update_job_posting_summary(
        ctx, UpdateJobPostingSummaryInput(posting_id=saved.posting.id, summary="要約")
    )
    detail = job_postings.get_job_posting(ctx, GetJobPostingInput(posting_id=saved.posting.id))
    assert (detail.summary, detail.raw_text) == ("要約", "求人")


def test_oversized_job_posting_is_rejected(ctx: AppContext) -> None:
    target = new_application(ctx)
    with pytest.raises(ContentTooLargeError):
        posting(ctx, target.id, "あ" * (ctx.settings.max_raw_text_chars + 1))


def test_get_application_includes_postings(ctx: AppContext) -> None:
    target = new_application(ctx)
    posting(ctx, target.id)
    detail = application.get_application(ctx, GetApplicationInput(application_id=target.id))
    assert len(detail.job_postings) == 1


def test_priority_is_set_per_application_of_the_same_company(ctx: AppContext) -> None:
    first = new_application(ctx, priority=90)
    second = application.add_application(
        ctx, AddApplicationInput(company_id=first.company_id, position="SRE", priority=60)
    )
    assert (first.priority, second.priority) == (90, 60)
    assert (
        application.get_application(ctx, GetApplicationInput(application_id=first.id)).priority
        == 90
    )


def test_priority_defaults_to_50(ctx: AppContext) -> None:
    assert new_application(ctx).priority == 50


def test_priority_can_be_changed_but_not_cleared(ctx: AppContext) -> None:
    created = new_application(ctx, priority=0)
    kept = application.update_application(
        ctx, UpdateApplicationInput(application_id=created.id, memo="x")
    )
    assert kept.priority == 0
    changed = application.update_application(
        ctx, UpdateApplicationInput(application_id=created.id, priority=70)
    )
    assert changed.priority == 70
    ignored = application.update_application(
        ctx, UpdateApplicationInput(application_id=created.id, priority=None)
    )
    assert ignored.priority == 70


def test_find_sorts_by_priority(ctx: AppContext) -> None:
    for name, priority in (("低", 0), ("高", 100), ("中", 55)):
        new_application(ctx, name, priority=priority)

    def names(**values) -> list[str]:  # type: ignore[no-untyped-def]
        found = application.find_applications(ctx, FindApplicationsInput(**values))
        return [a.company_name for a in found.items]

    assert names(sort=ApplicationSort.PRIORITY_DESC) == ["高", "中", "低"]
    assert names(sort=ApplicationSort.PRIORITY_ASC) == ["低", "中", "高"]
    assert names()[0] == "中"
    assert names(min_priority=55, sort=ApplicationSort.PRIORITY_DESC) == ["高", "中"]


@pytest.mark.parametrize("priority", [-1, 101])
def test_priority_must_be_within_100_points(priority: int) -> None:
    with pytest.raises(ValidationError):
        AddApplicationInput(
            new_company=NewCompanyInput(name="A社"), position="SWE", priority=priority
        )
