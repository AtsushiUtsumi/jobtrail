from uuid import UUID

from jobtrail.domain.application.job_posting import JobPostingSnapshot
from jobtrail.domain.company.company_source import SaveResult
from jobtrail.domain.shared.errors import NotFoundError
from jobtrail.domain.shared.value_objects import ensure_text_size
from jobtrail.schemas.application import (
    GetJobPostingInput,
    GetJobPostingsInput,
    JobPostingDetail,
    JobPostingList,
    JobPostingOutput,
    SaveJobPostingInput,
    SaveJobPostingOutput,
    UpdateJobPostingSummaryInput,
)
from jobtrail.usecase.application.commands import load_application
from jobtrail.usecase.context import AppContext, UnitOfWork


def _load_posting(uow: UnitOfWork, posting_id: UUID) -> JobPostingSnapshot:
    posting = uow.job_postings.get(posting_id)
    if posting is None:
        raise NotFoundError("求人票", posting_id, "get_job_postings で ID を確認してください。")
    return posting


def save_job_posting(ctx: AppContext, data: SaveJobPostingInput) -> SaveJobPostingOutput:
    """求人票の版を保存する。最新版と同じ本文なら新しい版を作らない。"""
    ensure_text_size(data.raw_text, ctx.settings.max_raw_text_chars)
    with ctx.uow_factory() as uow:
        application = load_application(uow, data.application_id)
        previous = uow.job_postings.latest(application.id)
        if previous is not None and previous.is_same_content(data.raw_text):
            return SaveJobPostingOutput(
                result=SaveResult.UNCHANGED,
                posting=JobPostingOutput.model_validate(previous),
            )
        posting = JobPostingSnapshot.capture(
            application.id,
            data.url,
            data.raw_text,
            ctx.now(),
            previous,
            summary=data.summary,
            salary_range=data.salary_range.to_domain() if data.salary_range else None,
            location=data.location,
            employment_type=data.employment_type,
            remote_policy=data.remote_policy,
            tech_stack=data.tech_stack,
            required=data.required,
            preferred=data.preferred,
            extra=data.extra,
            acquired_by=data.acquired_by,
        )
        uow.job_postings.add(posting)
        uow.commit()
        return SaveJobPostingOutput(
            result=SaveResult.NEW_REVISION if previous else SaveResult.CREATED,
            posting=JobPostingOutput.model_validate(posting),
        )


def get_job_postings(ctx: AppContext, data: GetJobPostingsInput) -> JobPostingList:
    """応募の求人票の版を本文なしで一覧する。"""
    with ctx.uow_factory() as uow:
        load_application(uow, data.application_id)
        postings = uow.job_postings.list_for_application(data.application_id)
        return JobPostingList(items=[JobPostingOutput.model_validate(p) for p in postings])


def get_job_posting(ctx: AppContext, data: GetJobPostingInput) -> JobPostingDetail:
    """求人票の版を本文つきで取得する。"""
    with ctx.uow_factory() as uow:
        return JobPostingDetail.model_validate(_load_posting(uow, data.posting_id))


def update_job_posting_summary(
    ctx: AppContext, data: UpdateJobPostingSummaryInput
) -> JobPostingOutput:
    """求人票の要約を更新する。本文は変更できない。"""
    with ctx.uow_factory() as uow:
        posting = _load_posting(uow, data.posting_id)
        posting.update_summary(data.summary)
        uow.commit()
        return JobPostingOutput.model_validate(posting)
