from datetime import datetime
from typing import Annotated, Any, Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from jobtrail.domain.application.application import DEFAULT_PRIORITY
from jobtrail.domain.application.repository import ApplicationSort
from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import (
    ApplicationChannel,
    ApplicationStatus,
    Outcome,
    SalaryRange,
)
from jobtrail.domain.company.company_source import AcquiredBy, SaveResult
from jobtrail.domain.skill_profile.submission import SubmissionKind
from jobtrail.schemas.common import InputModel, OutputModel, PageInput, Timestamp

Priority = Annotated[int, Field(ge=0, le=100, description="志望度（100 点満点）")]


class NewCompanyInput(InputModel):
    name: str = Field(min_length=1)
    url: str | None = None


class AddApplicationInput(InputModel):
    company_id: UUID | None = Field(default=None, description="登録済み企業の ID")
    new_company: NewCompanyInput | None = Field(default=None, description="未登録の企業を同時作成")
    position: str = Field(min_length=1)
    channel: ApplicationChannel = ApplicationChannel.DIRECT
    agent_name: str | None = None
    priority: Priority = DEFAULT_PRIORITY
    memo: str = ""

    @model_validator(mode="after")
    def exactly_one_company(self) -> Self:
        if (self.company_id is None) == (self.new_company is None):
            raise ValueError("company_id と new_company のどちらか一方を指定してください")
        return self


class UpdateApplicationInput(InputModel):
    application_id: UUID
    position: str | None = Field(default=None, min_length=1)
    channel: ApplicationChannel | None = None
    agent_name: str | None = None
    priority: Priority | None = None
    memo: str | None = None
    expected_version: int | None = None


class ApplyInput(InputModel):
    application_id: UUID
    applied_at: Timestamp
    expected_version: int | None = None


class CloseApplicationInput(InputModel):
    application_id: UUID
    outcome: Outcome
    expected_version: int | None = None


class ReopenApplicationInput(InputModel):
    application_id: UUID
    expected_version: int | None = None


class GetApplicationInput(InputModel):
    application_id: UUID


class FindApplicationsInput(PageInput):
    statuses: list[ApplicationStatus] | None = Field(
        default=None, description="いずれかに一致する応募を返す。省略時は全ステータス"
    )
    outcome: Outcome | None = None
    company_id: UUID | None = None
    channel: ApplicationChannel | None = None
    applied_from: Timestamp | None = None
    applied_to: Timestamp | None = None
    query: str | None = Field(default=None, description="社名・職種の部分一致")
    min_priority: Priority | None = None
    sort: ApplicationSort = Field(
        default=ApplicationSort.UPDATED_DESC,
        description="並び順。同点なら更新が新しい順",
    )


class AdvanceStageInput(InputModel):
    application_id: UUID
    type: StageType
    label: str | None = None
    scheduled_at: Timestamp | None = None
    memo: str = ""
    expected_version: int | None = None


class RecordStageResultInput(InputModel):
    application_id: UUID
    stage_id: UUID
    result: StageResult
    memo: str | None = None
    expected_version: int | None = None


class RescheduleStageInput(InputModel):
    application_id: UUID
    stage_id: UUID
    scheduled_at: Timestamp | None
    expected_version: int | None = None


class UpdateStageMemoInput(InputModel):
    application_id: UUID
    stage_id: UUID
    memo: str
    expected_version: int | None = None


class StageOutput(OutputModel):
    id: UUID
    type: StageType
    label: str | None
    scheduled_at: Timestamp | None
    result: StageResult
    memo: str
    created_at: Timestamp
    result_recorded_at: Timestamp | None


class ApplicationSummary(BaseModel):
    """一覧・カンバン用の表現。status は導出値。"""

    id: UUID
    company_id: UUID
    company_name: str
    position: str
    channel: ApplicationChannel
    priority: int
    applied_at: datetime | None
    outcome: Outcome
    status: ApplicationStatus
    stage_type: StageType | None
    current_stage_id: UUID | None
    current_stage_result: StageResult | None
    next_scheduled_at: datetime | None
    has_submitted_document: bool
    updated_at: datetime
    version: int


class SalaryRangeSchema(OutputModel):
    minimum: int | None = None
    maximum: int | None = None
    currency: str = "JPY"
    period: str = Field(default="year", description="year / month / hour")

    def to_domain(self) -> SalaryRange:
        return SalaryRange(self.minimum, self.maximum, self.currency, self.period)


class SaveJobPostingInput(InputModel):
    application_id: UUID
    url: str | None = None
    raw_text: str = Field(min_length=1)
    summary: str = ""
    salary_range: SalaryRangeSchema | None = None
    location: str | None = None
    employment_type: str | None = None
    remote_policy: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    required: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
    acquired_by: AcquiredBy = AcquiredBy.CLAUDE_FETCH


class GetJobPostingsInput(InputModel):
    application_id: UUID


class GetJobPostingInput(InputModel):
    posting_id: UUID


class UpdateJobPostingSummaryInput(InputModel):
    posting_id: UUID
    summary: str


class JobPostingOutput(OutputModel):
    """本文を含まない一覧用の表現。"""

    id: UUID
    application_id: UUID
    url: str | None
    fetched_at: Timestamp
    content_hash: str
    summary: str
    salary_range: SalaryRangeSchema | None
    location: str | None
    employment_type: str | None
    remote_policy: str | None
    tech_stack: list[str]
    required: list[str]
    preferred: list[str]
    extra: dict[str, Any]
    acquired_by: AcquiredBy
    revision: int


class JobPostingDetail(JobPostingOutput):
    raw_text: str


class JobPostingList(BaseModel):
    items: list[JobPostingOutput]


class SaveJobPostingOutput(BaseModel):
    result: SaveResult
    posting: JobPostingOutput


class SubmissionOutput(OutputModel):
    """snapshot を含まない一覧用の表現。"""

    id: UUID
    application_id: UUID
    submitted_at: Timestamp
    kind: SubmissionKind
    template_file_name: str | None
    received_at: Timestamp | None
    document_version_id: UUID | None
    memo: str


class SubmissionDetail(SubmissionOutput):
    snapshot: dict[str, Any]


class ApplicationOutput(BaseModel):
    id: UUID
    company_id: UUID
    company_name: str
    position: str
    channel: ApplicationChannel
    agent_name: str | None
    priority: int
    applied_at: datetime | None
    outcome: Outcome
    status: ApplicationStatus
    stage_type: StageType | None
    stages: list[StageOutput]
    submitted_document_version_id: UUID | None
    memo: str
    created_at: datetime
    updated_at: datetime
    version: int


class ApplicationDetail(ApplicationOutput):
    job_postings: list[JobPostingOutput]
    submissions: list[SubmissionOutput]
