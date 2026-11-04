from datetime import datetime, timedelta

from jobtrail.domain.application.repository import ApplicationRow
from jobtrail.domain.application.stage import StageResult
from jobtrail.domain.application.value_objects import Outcome
from jobtrail.schemas.analytics import (
    GetNextActionsInput,
    NextActionsOutput,
    UpcomingStage,
    WaitingApplication,
)
from jobtrail.schemas.company import CompanySourceOutput
from jobtrail.usecase.application.presenters import to_summary
from jobtrail.usecase.context import AppContext

STALE_SOURCE_LIMIT = 50


def _waiting_since(row: ApplicationRow, now: datetime) -> datetime | None:
    """結果待ちの起点。予定日が過ぎていれば予定日、未定なら Stage の追加日。"""
    if row.outcome is not Outcome.IN_PROGRESS or not row.stages:
        return None
    last = row.stages[-1]
    if last.result is not StageResult.PENDING:
        return None
    if last.scheduled_at is None:
        return last.created_at
    return last.scheduled_at if last.scheduled_at <= now else None


def get_next_actions(ctx: AppContext, data: GetNextActionsInput) -> NextActionsOutput:
    """近日の予定、結果待ちが長い応募、古い企業情報、提出書類が未紐づけの応募を返す。"""
    settings = ctx.settings
    now = ctx.now()

    def days(value: int | None, default: int) -> timedelta:
        return timedelta(days=default if value is None else value)

    horizon = now + days(data.upcoming_days, settings.upcoming_days)
    waiting_limit = days(data.stale_waiting_days, settings.stale_waiting_days)
    source_cutoff = now - days(data.stale_source_days, settings.stale_source_days)

    with ctx.uow_factory() as uow:
        rows = list(uow.application_reads.rows())
        sources, _ = uow.company_sources.find_stale(source_cutoff, STALE_SOURCE_LIMIT, 0)
        stale_sources = [CompanySourceOutput.model_validate(s) for s in sources]

    upcoming = []
    waiting = []
    missing = []
    for row in rows:
        summary = to_summary(row)
        scheduled = summary.next_scheduled_at
        if scheduled is not None and now <= scheduled <= horizon:
            upcoming.append(UpcomingStage(application=summary, scheduled_at=scheduled))
        since = _waiting_since(row, now)
        if since is not None and now - since > waiting_limit:
            waiting.append(WaitingApplication(application=summary, waiting_days=(now - since).days))
        if (
            row.applied_at is not None
            and row.outcome is Outcome.IN_PROGRESS
            and not summary.has_submitted_document
        ):
            missing.append(summary)
    upcoming.sort(key=lambda u: u.scheduled_at)
    waiting.sort(key=lambda w: w.waiting_days, reverse=True)
    return NextActionsOutput(
        upcoming_stages=upcoming,
        waiting_too_long=waiting,
        stale_sources=stale_sources,
        missing_documents=missing,
    )
