from pydantic import BaseModel, Field

from jobtrail.domain.application.repository import ApplicationSort
from jobtrail.domain.application.stage import StageType
from jobtrail.domain.application.value_objects import ApplicationChannel, ApplicationStatus
from jobtrail.schemas.application import ApplicationSummary
from jobtrail.schemas.common import InputModel, Timestamp
from jobtrail.schemas.company import CompanySourceOutput


class GetPipelineInput(InputModel):
    include_closed: bool = True
    sort: ApplicationSort = Field(
        default=ApplicationSort.UPDATED_DESC,
        description="各列の並び順。同点なら更新が新しい順",
    )


class PipelineColumn(BaseModel):
    status: ApplicationStatus
    count: int
    items: list[ApplicationSummary]


class PipelineOutput(BaseModel):
    columns: list[PipelineColumn]
    total: int


class StagePassRate(BaseModel):
    stage_type: StageType
    entered: int
    decided: int
    passed: int
    pass_rate: float | None


class ChannelStats(BaseModel):
    channel: ApplicationChannel
    applied: int
    offers: int
    rejected: int
    offer_rate: float | None


class DaysToOffer(BaseModel):
    count: int
    average: float | None
    median: float | None


class StatsOutput(BaseModel):
    applied_total: int = Field(description="分母。検討中・見送りは含まない")
    stage_pass_rates: list[StagePassRate]
    days_to_offer: DaysToOffer
    channels: list[ChannelStats]


class GetNextActionsInput(InputModel):
    upcoming_days: int | None = Field(default=None, ge=0)
    stale_waiting_days: int | None = Field(default=None, ge=0)
    stale_source_days: int | None = Field(default=None, ge=0)


class UpcomingStage(BaseModel):
    application: ApplicationSummary
    scheduled_at: Timestamp


class WaitingApplication(BaseModel):
    application: ApplicationSummary
    waiting_days: int


class NextActionsOutput(BaseModel):
    upcoming_stages: list[UpcomingStage]
    waiting_too_long: list[WaitingApplication]
    stale_sources: list[CompanySourceOutput]
    missing_documents: list[ApplicationSummary]
