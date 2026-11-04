from datetime import UTC, datetime
from typing import Any

from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.schemas.application import (
    AddApplicationInput,
    AdvanceStageInput,
    ApplicationOutput,
    ApplyInput,
    NewCompanyInput,
    RecordStageResultInput,
)
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.context import AppContext

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def new_application(ctx: AppContext, name: str = "アクメ", **values: Any) -> ApplicationOutput:
    return application.add_application(
        ctx,
        AddApplicationInput(new_company=NewCompanyInput(name=name), position="SWE", **values),
    )


def applied(ctx: AppContext, name: str = "アクメ", **values: Any) -> ApplicationOutput:
    created = new_application(ctx, name, **values)
    return application.apply(ctx, ApplyInput(application_id=created.id, applied_at=NOW))


def stage(
    ctx: AppContext,
    target: ApplicationOutput,
    type: StageType,
    result: StageResult | None = None,
    scheduled_at: datetime | None = None,
) -> ApplicationOutput:
    updated = application.advance_stage(
        ctx, AdvanceStageInput(application_id=target.id, type=type, scheduled_at=scheduled_at)
    )
    if result is None:
        return updated
    return application.record_stage_result(
        ctx,
        RecordStageResultInput(
            application_id=target.id, stage_id=updated.stages[-1].id, result=result
        ),
    )
