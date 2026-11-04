from jobtrail.domain.application.value_objects import ApplicationStatus
from jobtrail.schemas.analytics import GetPipelineInput, PipelineColumn, PipelineOutput
from jobtrail.usecase.application.presenters import to_summary
from jobtrail.usecase.context import AppContext


def get_pipeline(ctx: AppContext, data: GetPipelineInput) -> PipelineOutput:
    """ステータス別の応募一覧を返す（カンバン用）。"""
    with ctx.uow_factory() as uow:
        summaries = [to_summary(row) for row in uow.application_reads.rows()]
    statuses = [s for s in ApplicationStatus if data.include_closed or s is not s.CLOSED]
    columns = []
    for status in statuses:
        items = [s for s in summaries if s.status is status]
        items.sort(key=lambda s: s.updated_at, reverse=True)
        columns.append(PipelineColumn(status=status, count=len(items), items=items))
    return PipelineOutput(columns=columns, total=sum(c.count for c in columns))
