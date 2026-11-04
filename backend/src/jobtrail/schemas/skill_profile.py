from typing import Any
from uuid import UUID

from pydantic import Field

from jobtrail.domain.skill_profile.skill_profile import Disclosure
from jobtrail.domain.skill_profile.submission import SubmissionKind
from jobtrail.schemas.common import InputModel, OutputModel, PageInput, Timestamp, YearMonth


class BasicFields(InputModel):
    full_name: str = ""
    birth_date: str | None = None
    age: int | None = Field(default=None, ge=0)
    nearest_station: str = ""
    desired_conditions: str = ""
    self_pr: str = ""
    strengths_summary: str = ""


class CareerFields(InputModel):
    company_name: str = Field(min_length=1)
    start: YearMonth | None = None
    end: YearMonth | None = None
    employment_type: str = ""
    role: str = ""
    summary: str = ""


class ProjectFields(InputModel):
    summary: str = Field(min_length=1)
    start: YearMonth | None = None
    end: YearMonth | None = Field(default=None, description="省略時は現在も継続中")
    role: str = ""
    team_size: int | None = Field(default=None, ge=0)
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    infrastructure: list[str] = Field(default_factory=list)
    phases: list[str] = Field(default_factory=list)
    achievements: str = ""
    disclosure: Disclosure = Field(
        default=Disclosure.PUBLIC, description="public / anonymized / private"
    )
    anonymized_name: str | None = None


class SkillFields(InputModel):
    name: str = Field(min_length=1)
    category: str = ""
    years: float | None = Field(default=None, ge=0)
    proficiency: str = ""


class QualificationFields(InputModel):
    name: str = Field(min_length=1)
    acquired_on: YearMonth | None = None


class GetSkillProfileInput(InputModel):
    technology: str | None = Field(default=None, description="技術名で絞り込む")
    recent_years: int | None = Field(default=None, ge=1, description="直近 N 年の案件に絞る")
    disclosure: Disclosure | None = None


class UpdateBasicInput(InputModel):
    full_name: str | None = None
    birth_date: str | None = None
    age: int | None = Field(default=None, ge=0)
    nearest_station: str | None = None
    desired_conditions: str | None = None
    self_pr: str | None = None
    strengths_summary: str | None = None
    expected_version: int | None = None


class AddCareerInput(CareerFields):
    expected_version: int | None = None


class UpdateCareerInput(InputModel):
    career_id: UUID
    company_name: str | None = Field(default=None, min_length=1)
    start: YearMonth | None = None
    end: YearMonth | None = None
    employment_type: str | None = None
    role: str | None = None
    summary: str | None = None
    expected_version: int | None = None


class RemoveCareerInput(InputModel):
    career_id: UUID
    expected_version: int | None = None


class AddProjectInput(ProjectFields):
    expected_version: int | None = None


class UpdateProjectInput(InputModel):
    project_id: UUID
    summary: str | None = Field(default=None, min_length=1)
    start: YearMonth | None = None
    end: YearMonth | None = None
    role: str | None = None
    team_size: int | None = Field(default=None, ge=0)
    languages: list[str] | None = None
    frameworks: list[str] | None = None
    databases: list[str] | None = None
    infrastructure: list[str] | None = None
    phases: list[str] | None = None
    achievements: str | None = None
    disclosure: Disclosure | None = None
    anonymized_name: str | None = None
    expected_version: int | None = None


class RemoveProjectInput(InputModel):
    project_id: UUID
    expected_version: int | None = None


class AddSkillInput(SkillFields):
    expected_version: int | None = None


class UpdateSkillInput(InputModel):
    skill_id: UUID
    name: str | None = Field(default=None, min_length=1)
    category: str | None = None
    years: float | None = Field(default=None, ge=0)
    proficiency: str | None = None
    expected_version: int | None = None


class RemoveSkillInput(InputModel):
    skill_id: UUID
    expected_version: int | None = None


class AddQualificationInput(QualificationFields):
    expected_version: int | None = None


class UpdateQualificationInput(InputModel):
    qualification_id: UUID
    name: str | None = Field(default=None, min_length=1)
    acquired_on: YearMonth | None = None
    expected_version: int | None = None


class RemoveQualificationInput(InputModel):
    qualification_id: UUID
    expected_version: int | None = None


class ImportSkillProfileInput(InputModel):
    basic: BasicFields = Field(default_factory=BasicFields)
    careers: list[CareerFields] = Field(default_factory=list)
    projects: list[ProjectFields] = Field(default_factory=list)
    skills: list[SkillFields] = Field(default_factory=list)
    qualifications: list[QualificationFields] = Field(default_factory=list)
    overwrite: bool = Field(default=False, description="既存の内容を全て置き換える場合に true")


class BasicOutput(OutputModel):
    full_name: str
    birth_date: str | None
    age: int | None
    nearest_station: str
    desired_conditions: str
    self_pr: str
    strengths_summary: str


class CareerOutput(OutputModel):
    id: UUID
    company_name: str
    start: str | None
    end: str | None
    employment_type: str
    role: str
    summary: str


class ProjectOutput(OutputModel):
    id: UUID
    summary: str
    start: str | None
    end: str | None
    role: str
    team_size: int | None
    languages: list[str]
    frameworks: list[str]
    databases: list[str]
    infrastructure: list[str]
    phases: list[str]
    achievements: str
    disclosure: Disclosure
    anonymized_name: str | None


class SkillOutput(OutputModel):
    id: UUID
    name: str
    category: str
    years: float | None
    proficiency: str


class QualificationOutput(OutputModel):
    id: UUID
    name: str
    acquired_on: str | None


class SkillProfileOutput(OutputModel):
    basic: BasicOutput
    careers: list[CareerOutput]
    projects: list[ProjectOutput]
    skills: list[SkillOutput]
    qualifications: list[QualificationOutput]
    version: int
    updated_at: Timestamp | None


class RecordSubmissionInput(InputModel):
    application_id: UUID
    submitted_at: Timestamp
    kind: SubmissionKind = SubmissionKind.SKILL_SHEET
    template_file_name: str | None = Field(default=None, description="企業から受け取った様式の名前")
    received_at: Timestamp | None = None
    snapshot: dict[str, Any] | None = Field(
        default=None,
        description="提出内容。省略時は現在の SkillProfile 全体を記録する",
    )
    document_version_id: UUID | None = None
    memo: str = ""


class ListSubmissionsInput(PageInput):
    application_id: UUID | None = None


class GetSubmissionInput(InputModel):
    submission_id: UUID
