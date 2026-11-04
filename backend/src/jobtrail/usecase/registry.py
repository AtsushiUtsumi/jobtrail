"""ユースケースの唯一の登録先。REST ルートと MCP ツールはここから生成する。"""

from collections.abc import Callable
from dataclasses import dataclass
from functools import cached_property
from inspect import getdoc
from typing import Any, get_type_hints

from pydantic import BaseModel

from jobtrail.usecase import health
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.application import job_postings
from jobtrail.usecase.company import commands as company
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.document import commands as document
from jobtrail.usecase.query.next_actions import get_next_actions
from jobtrail.usecase.query.pipeline import get_pipeline
from jobtrail.usecase.query.stats import get_stats
from jobtrail.usecase.skill_profile import commands as skill_profile


@dataclass(frozen=True)
class UseCase:
    handler: Callable[[AppContext, Any], BaseModel]
    method: str
    path: str
    status_code: int = 200

    @property
    def name(self) -> str:
        return self.handler.__name__

    @property
    def description(self) -> str:
        return getdoc(self.handler) or ""

    @cached_property
    def input_model(self) -> type[BaseModel]:
        hints = get_type_hints(self.handler)
        model: type[BaseModel] = hints["data"]
        return model

    @cached_property
    def output_model(self) -> type[BaseModel]:
        model: type[BaseModel] = get_type_hints(self.handler)["return"]
        return model

    @property
    def read_only(self) -> bool:
        return self.method == "GET"

    @property
    def destructive(self) -> bool:
        return self.method == "DELETE"

    def execute(self, ctx: AppContext, arguments: dict[str, Any]) -> BaseModel:
        return self.handler(ctx, self.input_model.model_validate(arguments))


USE_CASES: tuple[UseCase, ...] = (
    UseCase(health.ping, "GET", "/health"),
    # 企業
    UseCase(company.register_company, "POST", "/companies", 201),
    UseCase(company.find_companies, "GET", "/companies"),
    UseCase(company.get_company, "GET", "/companies/{company_id}"),
    UseCase(company.update_company, "PATCH", "/companies/{company_id}"),
    UseCase(company.delete_company, "DELETE", "/companies/{company_id}"),
    UseCase(company.restore_company, "POST", "/companies/{company_id}/restore"),
    UseCase(company.save_company_source, "POST", "/companies/{company_id}/sources", 201),
    UseCase(company.get_company_sources, "GET", "/companies/{company_id}/sources"),
    UseCase(company.find_stale_company_sources, "GET", "/company-sources/stale"),
    UseCase(company.get_company_source, "GET", "/company-sources/{source_id}"),
    UseCase(company.update_company_source_summary, "PATCH", "/company-sources/{source_id}"),
    # 応募
    UseCase(application.add_application, "POST", "/applications", 201),
    UseCase(application.find_applications, "GET", "/applications"),
    UseCase(application.get_application, "GET", "/applications/{application_id}"),
    UseCase(application.update_application, "PATCH", "/applications/{application_id}"),
    UseCase(application.apply, "POST", "/applications/{application_id}/apply"),
    UseCase(application.close_application, "POST", "/applications/{application_id}/close"),
    UseCase(application.reopen_application, "POST", "/applications/{application_id}/reopen"),
    UseCase(application.advance_stage, "POST", "/applications/{application_id}/stages", 201),
    UseCase(
        application.record_stage_result,
        "POST",
        "/applications/{application_id}/stages/{stage_id}/result",
    ),
    UseCase(
        application.reschedule_stage,
        "POST",
        "/applications/{application_id}/stages/{stage_id}/schedule",
    ),
    UseCase(
        application.update_stage_memo,
        "POST",
        "/applications/{application_id}/stages/{stage_id}/memo",
    ),
    UseCase(job_postings.save_job_posting, "POST", "/applications/{application_id}/postings", 201),
    UseCase(job_postings.get_job_postings, "GET", "/applications/{application_id}/postings"),
    UseCase(job_postings.get_job_posting, "GET", "/job-postings/{posting_id}"),
    UseCase(job_postings.update_job_posting_summary, "PATCH", "/job-postings/{posting_id}"),
    # 書類
    UseCase(document.create_document, "POST", "/documents", 201),
    UseCase(document.list_documents, "GET", "/documents"),
    UseCase(document.get_document, "GET", "/documents/{document_id}"),
    UseCase(document.add_document_version, "POST", "/documents/{document_id}/versions", 201),
    UseCase(
        document.attach_document_to_application,
        "POST",
        "/applications/{application_id}/document",
    ),
    # スキルシート
    UseCase(skill_profile.get_skill_profile, "GET", "/skill-profile"),
    UseCase(skill_profile.update_skill_profile_basic, "PATCH", "/skill-profile/basic"),
    UseCase(skill_profile.import_skill_profile, "POST", "/skill-profile/import"),
    UseCase(skill_profile.add_career, "POST", "/skill-profile/careers", 201),
    UseCase(skill_profile.update_career, "PATCH", "/skill-profile/careers/{career_id}"),
    UseCase(skill_profile.remove_career, "DELETE", "/skill-profile/careers/{career_id}"),
    UseCase(skill_profile.add_project, "POST", "/skill-profile/projects", 201),
    UseCase(skill_profile.update_project, "PATCH", "/skill-profile/projects/{project_id}"),
    UseCase(skill_profile.remove_project, "DELETE", "/skill-profile/projects/{project_id}"),
    UseCase(skill_profile.add_skill, "POST", "/skill-profile/skills", 201),
    UseCase(skill_profile.update_skill, "PATCH", "/skill-profile/skills/{skill_id}"),
    UseCase(skill_profile.remove_skill, "DELETE", "/skill-profile/skills/{skill_id}"),
    UseCase(skill_profile.add_qualification, "POST", "/skill-profile/qualifications", 201),
    UseCase(
        skill_profile.update_qualification,
        "PATCH",
        "/skill-profile/qualifications/{qualification_id}",
    ),
    UseCase(
        skill_profile.remove_qualification,
        "DELETE",
        "/skill-profile/qualifications/{qualification_id}",
    ),
    UseCase(skill_profile.record_submission, "POST", "/submissions", 201),
    UseCase(skill_profile.list_submissions, "GET", "/submissions"),
    UseCase(skill_profile.get_submission, "GET", "/submissions/{submission_id}"),
    # 分析
    UseCase(get_pipeline, "GET", "/analytics/pipeline"),
    UseCase(get_stats, "GET", "/analytics/stats"),
    UseCase(get_next_actions, "GET", "/analytics/next-actions"),
)
