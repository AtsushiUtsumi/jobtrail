from dataclasses import replace
from datetime import UTC, datetime, timedelta

from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import (
    ApplicationChannel,
    ApplicationStatus,
    Outcome,
)
from jobtrail.domain.company.company_source import SourceType
from jobtrail.domain.document.document import DocumentKind
from jobtrail.schemas.analytics import GetNextActionsInput, GetPipelineInput
from jobtrail.schemas.application import CloseApplicationInput
from jobtrail.schemas.common import EmptyInput
from jobtrail.schemas.company import RegisterCompanyInput, SaveCompanySourceInput
from jobtrail.schemas.document import AttachDocumentInput, CreateDocumentInput
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.company import commands as company
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.document import commands as document
from jobtrail.usecase.query.next_actions import get_next_actions
from jobtrail.usecase.query.pipeline import get_pipeline
from jobtrail.usecase.query.stats import get_stats
from tests.usecase.helpers import applied, new_application, stage


def at(ctx: AppContext, moment: datetime) -> AppContext:
    return replace(ctx, now=lambda: moment)


def column(ctx: AppContext, status: ApplicationStatus) -> list[str]:
    pipeline = get_pipeline(ctx, GetPipelineInput())
    return next(
        [item.company_name for item in c.items] for c in pipeline.columns if c.status is status
    )


def test_pipeline_groups_by_derived_status(ctx: AppContext) -> None:
    new_application(ctx, "検討")
    applied(ctx, "応募")
    stage(ctx, applied(ctx, "選考"), StageType.INTERVIEW)
    stage(ctx, applied(ctx, "通過"), StageType.DOCUMENT, StageResult.PASSED)
    stage(ctx, applied(ctx, "内定"), StageType.OFFER, StageResult.PASSED)
    stage(ctx, applied(ctx, "不合格"), StageType.DOCUMENT, StageResult.REJECTED)

    assert column(ctx, ApplicationStatus.CONSIDERING) == ["検討"]
    assert column(ctx, ApplicationStatus.APPLIED) == ["応募"]
    assert column(ctx, ApplicationStatus.IN_STAGE) == ["選考"]
    assert column(ctx, ApplicationStatus.AWAITING_NEXT_STAGE) == ["通過"]
    assert column(ctx, ApplicationStatus.OFFER_PENDING) == ["内定"]
    assert column(ctx, ApplicationStatus.CLOSED) == ["不合格"]
    assert get_pipeline(ctx, GetPipelineInput()).total == 6

    open_only = get_pipeline(ctx, GetPipelineInput(include_closed=False))
    assert open_only.total == 5
    assert ApplicationStatus.CLOSED not in [c.status for c in open_only.columns]


def test_stats_exclude_considering_and_passed_over(ctx: AppContext) -> None:
    new_application(ctx, "検討")
    skipped = new_application(ctx, "見送り")
    application.close_application(
        ctx, CloseApplicationInput(application_id=skipped.id, outcome=Outcome.PASSED_OVER)
    )
    stats = get_stats(ctx, EmptyInput())
    assert stats.applied_total == 0
    assert stats.days_to_offer.count == 0
    assert all(rate.pass_rate is None for rate in stats.stage_pass_rates)


def test_stats_pass_rates_and_channels(ctx: AppContext) -> None:
    passed = applied(ctx, "A", channel=ApplicationChannel.AGENT)
    passed = stage(ctx, passed, StageType.DOCUMENT, StageResult.PASSED)
    stage(ctx, applied(ctx, "B"), StageType.DOCUMENT, StageResult.REJECTED)
    stage(ctx, applied(ctx, "C"), StageType.DOCUMENT)
    stage(ctx, passed, StageType.OFFER)

    stats = get_stats(ctx, EmptyInput())
    assert stats.applied_total == 3
    document_rate = next(r for r in stats.stage_pass_rates if r.stage_type is StageType.DOCUMENT)
    assert (document_rate.entered, document_rate.decided, document_rate.passed) == (3, 2, 1)
    assert document_rate.pass_rate == 0.5

    agent = next(c for c in stats.channels if c.channel is ApplicationChannel.AGENT)
    direct = next(c for c in stats.channels if c.channel is ApplicationChannel.DIRECT)
    assert (agent.applied, agent.offers, agent.offer_rate) == (1, 1, 1.0)
    assert (direct.applied, direct.offers, direct.rejected) == (2, 0, 1)


def test_days_to_offer_uses_offer_stage(ctx: AppContext) -> None:
    from tests.usecase.helpers import NOW

    target = applied(ctx)
    later = at(ctx, NOW + timedelta(days=10))
    stage(later, target, StageType.OFFER)
    stats = get_stats(ctx, EmptyInput())
    assert stats.days_to_offer.count == 1
    assert stats.days_to_offer.average == 10.0
    assert stats.days_to_offer.median == 10.0


def test_next_actions_upcoming_and_waiting(ctx: AppContext) -> None:
    now = datetime(2026, 3, 1, tzinfo=UTC)
    clock = at(ctx, now)
    stage(clock, applied(clock, "明日"), StageType.INTERVIEW, scheduled_at=now + timedelta(days=1))
    stage(clock, applied(clock, "来月"), StageType.INTERVIEW, scheduled_at=now + timedelta(days=30))
    stage(clock, applied(clock, "放置"), StageType.INTERVIEW, scheduled_at=now - timedelta(days=9))
    stage(clock, applied(clock, "直近"), StageType.INTERVIEW, scheduled_at=now - timedelta(days=3))
    stage(at(ctx, now - timedelta(days=20)), applied(clock, "未定"), StageType.DOCUMENT)

    actions = get_next_actions(clock, GetNextActionsInput())
    assert [u.application.company_name for u in actions.upcoming_stages] == ["明日"]
    assert [(w.application.company_name, w.waiting_days) for w in actions.waiting_too_long] == [
        ("未定", 20),
        ("放置", 9),
    ]

    wider = get_next_actions(clock, GetNextActionsInput(upcoming_days=60, stale_waiting_days=1))
    assert len(wider.upcoming_stages) == 2
    assert len(wider.waiting_too_long) == 3


def test_next_actions_missing_documents(ctx: AppContext) -> None:
    new_application(ctx, "検討")
    missing = applied(ctx, "未提出")
    done = applied(ctx, "提出済み")
    created = document.create_document(
        ctx, CreateDocumentInput(name="経歴", kind=DocumentKind.CAREER_HISTORY, body="本文")
    )
    document.attach_document_to_application(
        ctx,
        AttachDocumentInput(application_id=done.id, document_version_id=created.versions[0].id),
    )
    finished = applied(ctx, "終了")
    application.close_application(
        ctx, CloseApplicationInput(application_id=finished.id, outcome=Outcome.WITHDRAWN)
    )
    actions = get_next_actions(ctx, GetNextActionsInput())
    assert [a.id for a in actions.missing_documents] == [missing.id]


def test_next_actions_stale_sources(ctx: AppContext) -> None:
    now = datetime(2026, 6, 1, tzinfo=UTC)
    created = company.register_company(ctx, RegisterCompanyInput(name="A社"))
    company.save_company_source(
        at(ctx, now - timedelta(days=91)),
        SaveCompanySourceInput(
            company_id=created.id,
            source_type=SourceType.ABOUT,
            url="https://a.example",
            raw_text="本文",
        ),
    )
    assert len(get_next_actions(at(ctx, now), GetNextActionsInput()).stale_sources) == 1
    recent = at(ctx, now - timedelta(days=80))
    assert get_next_actions(recent, GetNextActionsInput()).stale_sources == []


def test_closed_application_is_not_listed_as_upcoming(ctx: AppContext) -> None:
    now = datetime(2026, 3, 1, tzinfo=UTC)
    clock = at(ctx, now)
    target = stage(
        clock, applied(clock, "辞退"), StageType.INTERVIEW, scheduled_at=now + timedelta(days=1)
    )
    application.close_application(
        clock, CloseApplicationInput(application_id=target.id, outcome=Outcome.WITHDRAWN)
    )
    assert get_next_actions(clock, GetNextActionsInput()).upcoming_stages == []
