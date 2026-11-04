from jobtrail.domain.application.application import Application, derive_status
from jobtrail.domain.application.repository import ApplicationRow
from jobtrail.domain.application.stage import StageResult
from jobtrail.domain.application.value_objects import Outcome
from jobtrail.schemas.application import ApplicationOutput, ApplicationSummary, StageOutput


def to_output(application: Application, company_name: str) -> ApplicationOutput:
    derived = application.derived_status
    return ApplicationOutput(
        id=application.id,
        company_id=application.company_id,
        company_name=company_name,
        position=application.position,
        channel=application.channel,
        agent_name=application.agent_name,
        applied_at=application.applied_at,
        outcome=application.outcome,
        status=derived.status,
        stage_type=derived.stage_type,
        stages=[StageOutput.model_validate(s) for s in application.stages],
        submitted_document_version_id=application.submitted_document_version_id,
        memo=application.memo,
        created_at=application.created_at,
        updated_at=application.updated_at,
        version=application.version,
    )


def to_summary(row: ApplicationRow) -> ApplicationSummary:
    derived = derive_status(row.outcome, row.applied_at, row.stages)
    last = row.stages[-1] if row.stages else None
    open_stage = last is not None and last.result is StageResult.PENDING
    pending = open_stage and row.outcome is Outcome.IN_PROGRESS
    return ApplicationSummary(
        id=row.id,
        company_id=row.company_id,
        company_name=row.company_name,
        position=row.position,
        channel=row.channel,
        applied_at=row.applied_at,
        outcome=row.outcome,
        status=derived.status,
        stage_type=derived.stage_type,
        current_stage_id=last.id if last else None,
        current_stage_result=last.result if last else None,
        next_scheduled_at=last.scheduled_at if last and pending else None,
        has_submitted_document=row.submitted_document_version_id is not None,
        updated_at=row.updated_at,
        version=row.version,
    )
