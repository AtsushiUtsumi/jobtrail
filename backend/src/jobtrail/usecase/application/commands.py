from collections.abc import Callable
from uuid import UUID

from jobtrail.domain.application.application import Application
from jobtrail.domain.shared.errors import DomainError, NotFoundError, check_version
from jobtrail.schemas.application import (
    AddApplicationInput,
    AdvanceStageInput,
    ApplicationDetail,
    ApplicationOutput,
    ApplicationSummary,
    ApplyInput,
    CloseApplicationInput,
    FindApplicationsInput,
    GetApplicationInput,
    JobPostingOutput,
    RecordStageResultInput,
    ReopenApplicationInput,
    RescheduleStageInput,
    SubmissionOutput,
    UpdateApplicationInput,
    UpdateStageMemoInput,
)
from jobtrail.schemas.common import Page
from jobtrail.usecase.application.presenters import sort_summaries, to_output, to_summary
from jobtrail.usecase.company.commands import create_company, load_company
from jobtrail.usecase.context import AppContext, UnitOfWork, changes_of

ALL_RECORDS_LIMIT = 200


def load_application(uow: UnitOfWork, application_id: UUID) -> Application:
    application = uow.applications.get(application_id)
    if application is None:
        raise NotFoundError("応募", application_id, "find_applications で ID を確認してください。")
    return application


def _mutate(
    ctx: AppContext,
    application_id: UUID,
    expected_version: int | None,
    change: Callable[[Application], object],
) -> ApplicationOutput:
    with ctx.uow_factory() as uow:
        application = load_application(uow, application_id)
        check_version(application.version, expected_version)
        change(application)
        uow.commit()
        return to_output(application, load_company(uow, application.company_id).name)


def add_application(ctx: AppContext, data: AddApplicationInput) -> ApplicationOutput:
    """応募を検討中の状態で追加する。企業が未登録なら new_company で同時に作成する。"""
    with ctx.uow_factory() as uow:
        if data.company_id is not None:
            company = load_company(uow, data.company_id)
            if company.is_deleted:
                raise DomainError(
                    "COMPANY_DELETED",
                    f"企業は削除済みです: {company.name}",
                    "restore_company で復元してから追加してください。",
                )
        else:
            assert data.new_company is not None
            new = data.new_company
            company = create_company(ctx, uow, new.name, new.url, "")
        application = Application.consider(
            company.id,
            data.position,
            data.channel,
            data.agent_name,
            data.memo,
            ctx.now(),
            data.priority,
        )
        uow.applications.add(application)
        uow.commit()
        return to_output(application, company.name)


def update_application(ctx: AppContext, data: UpdateApplicationInput) -> ApplicationOutput:
    """応募の職種・経路・エージェント名・志望度・メモを部分更新する。"""
    changes = changes_of(data, "application_id", nullable=frozenset({"agent_name"}))
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.update_details(ctx.now(), **changes),
    )


def apply(ctx: AppContext, data: ApplyInput) -> ApplicationOutput:
    """検討中の応募を応募済みにする。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.apply(data.applied_at, ctx.now()),
    )


def close_application(ctx: AppContext, data: CloseApplicationInput) -> ApplicationOutput:
    """応募を終了する（内定承諾・辞退・不合格・募集終了・見送りなど）。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.close(data.outcome, ctx.now()),
    )


def reopen_application(ctx: AppContext, data: ReopenApplicationInput) -> ApplicationOutput:
    """終了した応募を再開する。最後の不合格・辞退の Stage は結果待ちに戻る。"""
    return _mutate(ctx, data.application_id, data.expected_version, lambda a: a.reopen(ctx.now()))


def advance_stage(ctx: AppContext, data: AdvanceStageInput) -> ApplicationOutput:
    """次の Stage を追加する。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.add_stage(data.type, data.label, data.scheduled_at, data.memo, ctx.now()),
    )


def record_stage_result(ctx: AppContext, data: RecordStageResultInput) -> ApplicationOutput:
    """最新の Stage の結果を記録する。不合格・辞退なら応募は自動で終了する。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.record_stage_result(data.stage_id, data.result, data.memo, ctx.now()),
    )


def reschedule_stage(ctx: AppContext, data: RescheduleStageInput) -> ApplicationOutput:
    """Stage の日程を変更する。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.reschedule_stage(data.stage_id, data.scheduled_at, ctx.now()),
    )


def update_stage_memo(ctx: AppContext, data: UpdateStageMemoInput) -> ApplicationOutput:
    """Stage のメモを更新する。面接で聞かれたことはここに書く。"""
    return _mutate(
        ctx,
        data.application_id,
        data.expected_version,
        lambda a: a.update_stage_memo(data.stage_id, data.memo, ctx.now()),
    )


def find_applications(ctx: AppContext, data: FindApplicationsInput) -> Page[ApplicationSummary]:
    """ステータス・企業・経路・応募日の期間・キーワード・志望度で応募を検索する。"""
    needle = data.query.casefold() if data.query else None
    with ctx.uow_factory() as uow:
        rows = [
            row
            for row in uow.application_reads.rows()
            if (data.company_id is None or row.company_id == data.company_id)
            and (data.channel is None or row.channel is data.channel)
            and (data.outcome is None or row.outcome is data.outcome)
            and (data.min_priority is None or row.priority >= data.min_priority)
            and (
                data.applied_from is None
                or (row.applied_at is not None and row.applied_at >= data.applied_from)
            )
            and (
                data.applied_to is None
                or (row.applied_at is not None and row.applied_at <= data.applied_to)
            )
            and (
                needle is None
                or needle in row.company_name.casefold()
                or needle in row.position.casefold()
            )
        ]
    summaries = [to_summary(row) for row in rows]
    if data.statuses:
        summaries = [s for s in summaries if s.status in data.statuses]
    sort_summaries(summaries, data.sort)
    return Page(
        items=summaries[data.offset : data.offset + data.limit],
        total=len(summaries),
        limit=data.limit,
        offset=data.offset,
    )


def get_application(ctx: AppContext, data: GetApplicationInput) -> ApplicationDetail:
    """応募の詳細を Stage・求人票・提出記録つきで取得する。"""
    with ctx.uow_factory() as uow:
        application = load_application(uow, data.application_id)
        output = to_output(application, load_company(uow, application.company_id).name)
        postings = uow.job_postings.list_for_application(application.id)
        submissions, _ = uow.submissions.search(application.id, ALL_RECORDS_LIMIT, 0)
        return ApplicationDetail(
            **output.model_dump(),
            job_postings=[JobPostingOutput.model_validate(p) for p in postings],
            submissions=[SubmissionOutput.model_validate(s) for s in submissions],
        )
