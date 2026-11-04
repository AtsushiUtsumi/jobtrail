from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, Field

from jobtrail.domain.company.company_source import AcquiredBy, SaveResult, SourceType
from jobtrail.domain.company.repository import CompanyState
from jobtrail.schemas.common import InputModel, OutputModel, PageInput, Timestamp

Priority = Annotated[int, Field(ge=1, le=5, description="志望度（1=低 〜 5=高）")]


class ExtractedFields(BaseModel):
    """主要項目は固定キー、それ以外は extra に入れる。"""

    employee_count: int | None = None
    founded_year: int | None = None
    tech_stack: list[str] = Field(default_factory=list)
    remote_policy: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class RegisterCompanyInput(InputModel):
    name: str = Field(min_length=1)
    url: str | None = None
    priority: Priority | None = None
    memo: str = ""


class UpdateCompanyInput(InputModel):
    company_id: UUID
    name: str | None = Field(default=None, min_length=1)
    url: str | None = None
    priority: Priority | None = None
    memo: str | None = None
    expected_version: int | None = None


class CompanyVersionInput(InputModel):
    company_id: UUID
    expected_version: int | None = None


class GetCompanyInput(InputModel):
    company_id: UUID


class FindCompaniesInput(PageInput):
    query: str | None = Field(default=None, description="社名の部分一致（表記ゆれを吸収）")
    min_priority: Priority | None = None
    state: CompanyState = CompanyState.ACTIVE


class CompanyOutput(OutputModel):
    id: UUID
    name: str
    url: str | None
    priority: int | None
    memo: str
    created_at: Timestamp
    updated_at: Timestamp
    deleted_at: Timestamp | None
    version: int


class SaveCompanySourceInput(InputModel):
    company_id: UUID
    source_type: SourceType
    url: str = Field(min_length=1)
    raw_text: str = Field(min_length=1)
    summary: str = ""
    extracted_fields: ExtractedFields = Field(default_factory=ExtractedFields)
    acquired_by: AcquiredBy = AcquiredBy.CLAUDE_FETCH


class GetCompanySourcesInput(PageInput):
    company_id: UUID
    source_type: SourceType | None = None
    latest_only: bool = True


class GetCompanySourceInput(InputModel):
    source_id: UUID


class UpdateCompanySourceSummaryInput(InputModel):
    source_id: UUID
    summary: str
    extracted_fields: ExtractedFields | None = None


class FindStaleCompanySourcesInput(PageInput):
    older_than_days: int | None = Field(default=None, ge=0, description="省略時は既定の鮮度日数")


class CompanySourceOutput(OutputModel):
    """本文を含まない一覧用の表現。"""

    id: UUID
    company_id: UUID
    source_type: SourceType
    url: str
    fetched_at: Timestamp
    content_hash: str
    summary: str
    extracted_fields: dict[str, Any]
    acquired_by: AcquiredBy
    revision: int


class CompanySourceDetail(CompanySourceOutput):
    raw_text: str


class SaveCompanySourceOutput(BaseModel):
    result: SaveResult
    source: CompanySourceOutput
