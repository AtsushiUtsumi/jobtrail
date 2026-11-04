from collections.abc import Callable
from typing import Any

from jobtrail.domain.shared.errors import DomainError, NotFoundError, check_version
from jobtrail.domain.shared.ids import new_id
from jobtrail.domain.skill_profile.skill_profile import (
    Basic,
    Career,
    Project,
    Qualification,
    Skill,
    SkillProfile,
    add_item,
    remove_item,
    update_item,
)
from jobtrail.domain.skill_profile.submission import Submission
from jobtrail.schemas.application import SubmissionDetail, SubmissionOutput
from jobtrail.schemas.common import Page
from jobtrail.schemas.skill_profile import (
    AddCareerInput,
    AddProjectInput,
    AddQualificationInput,
    AddSkillInput,
    GetSkillProfileInput,
    GetSubmissionInput,
    ImportSkillProfileInput,
    ListSubmissionsInput,
    RecordSubmissionInput,
    RemoveCareerInput,
    RemoveProjectInput,
    RemoveQualificationInput,
    RemoveSkillInput,
    SkillProfileOutput,
    UpdateBasicInput,
    UpdateCareerInput,
    UpdateProjectInput,
    UpdateQualificationInput,
    UpdateSkillInput,
)
from jobtrail.usecase.application.commands import load_application
from jobtrail.usecase.context import AppContext, changes_of


def _mutate(
    ctx: AppContext, expected_version: int | None, change: Callable[[SkillProfile], Any]
) -> SkillProfileOutput:
    with ctx.uow_factory() as uow:
        profile = uow.skill_profile.get()
        check_version(profile.version, expected_version)
        change(profile)
        profile.updated_at = ctx.now()
        uow.skill_profile.save(profile)
        uow.commit()
        return SkillProfileOutput.model_validate(profile)


def get_skill_profile(ctx: AppContext, data: GetSkillProfileInput) -> SkillProfileOutput:
    """スキルシートを取得する。条件を渡すと案件・スキルを絞り込む。"""
    with ctx.uow_factory() as uow:
        profile = uow.skill_profile.get()
        uow.commit()
        filtered = profile.filtered(
            data.technology, data.recent_years, data.disclosure, ctx.now().date()
        )
        return SkillProfileOutput.model_validate(filtered)


def update_skill_profile_basic(ctx: AppContext, data: UpdateBasicInput) -> SkillProfileOutput:
    """スキルシートの基本情報を部分更新する。"""
    changes = changes_of(data, nullable=frozenset({"birth_date", "age"}))
    return _mutate(ctx, data.expected_version, lambda p: p.update_basic(**changes))


def add_career(ctx: AppContext, data: AddCareerInput) -> SkillProfileOutput:
    """職歴を追加する。"""
    values = data.model_dump(exclude={"expected_version"})
    return _mutate(ctx, data.expected_version, lambda p: add_item(p.careers, Career, **values))


def update_career(ctx: AppContext, data: UpdateCareerInput) -> SkillProfileOutput:
    """職歴を部分更新する。"""
    changes = changes_of(data, "career_id", nullable=frozenset({"start", "end"}))
    return _mutate(
        ctx, data.expected_version, lambda p: update_item(p.careers, data.career_id, **changes)
    )


def remove_career(ctx: AppContext, data: RemoveCareerInput) -> SkillProfileOutput:
    """職歴を削除する。"""
    return _mutate(ctx, data.expected_version, lambda p: remove_item(p.careers, data.career_id))


def add_project(ctx: AppContext, data: AddProjectInput) -> SkillProfileOutput:
    """案件を追加する。disclosure で公開可否、anonymized_name で匿名表記を指定する。"""
    values = data.model_dump(exclude={"expected_version"})
    return _mutate(ctx, data.expected_version, lambda p: add_item(p.projects, Project, **values))


def update_project(ctx: AppContext, data: UpdateProjectInput) -> SkillProfileOutput:
    """案件を部分更新する。"""
    changes = changes_of(
        data,
        "project_id",
        nullable=frozenset({"start", "end", "team_size", "anonymized_name"}),
    )
    return _mutate(
        ctx, data.expected_version, lambda p: update_item(p.projects, data.project_id, **changes)
    )


def remove_project(ctx: AppContext, data: RemoveProjectInput) -> SkillProfileOutput:
    """案件を削除する。"""
    return _mutate(ctx, data.expected_version, lambda p: remove_item(p.projects, data.project_id))


def add_skill(ctx: AppContext, data: AddSkillInput) -> SkillProfileOutput:
    """スキルを追加する。"""
    values = data.model_dump(exclude={"expected_version"})
    return _mutate(ctx, data.expected_version, lambda p: add_item(p.skills, Skill, **values))


def update_skill(ctx: AppContext, data: UpdateSkillInput) -> SkillProfileOutput:
    """スキルを部分更新する。"""
    changes = changes_of(data, "skill_id", nullable=frozenset({"years"}))
    return _mutate(
        ctx, data.expected_version, lambda p: update_item(p.skills, data.skill_id, **changes)
    )


def remove_skill(ctx: AppContext, data: RemoveSkillInput) -> SkillProfileOutput:
    """スキルを削除する。"""
    return _mutate(ctx, data.expected_version, lambda p: remove_item(p.skills, data.skill_id))


def add_qualification(ctx: AppContext, data: AddQualificationInput) -> SkillProfileOutput:
    """資格を追加する。"""
    values = data.model_dump(exclude={"expected_version"})
    return _mutate(
        ctx, data.expected_version, lambda p: add_item(p.qualifications, Qualification, **values)
    )


def update_qualification(ctx: AppContext, data: UpdateQualificationInput) -> SkillProfileOutput:
    """資格を部分更新する。"""
    changes = changes_of(data, "qualification_id", nullable=frozenset({"acquired_on"}))
    return _mutate(
        ctx,
        data.expected_version,
        lambda p: update_item(p.qualifications, data.qualification_id, **changes),
    )


def remove_qualification(ctx: AppContext, data: RemoveQualificationInput) -> SkillProfileOutput:
    """資格を削除する。"""
    return _mutate(
        ctx, data.expected_version, lambda p: remove_item(p.qualifications, data.qualification_id)
    )


def import_skill_profile(ctx: AppContext, data: ImportSkillProfileInput) -> SkillProfileOutput:
    """既存のスキルシートを構造化 JSON で一括投入する。内容があれば overwrite=true が必要。"""

    def replace_all(profile: SkillProfile) -> None:
        if not profile.is_empty and not data.overwrite:
            raise DomainError(
                "SKILL_PROFILE_NOT_EMPTY",
                "スキルシートには既に内容があります。",
                "置き換えてよいか確認のうえ overwrite=true を指定してください。",
            )
        profile.basic = Basic(**data.basic.model_dump())
        profile.careers = [Career(id=new_id(), **c.model_dump()) for c in data.careers]
        profile.projects = [Project(id=new_id(), **p.model_dump()) for p in data.projects]
        profile.skills = [Skill(id=new_id(), **s.model_dump()) for s in data.skills]
        profile.qualifications = [
            Qualification(id=new_id(), **q.model_dump()) for q in data.qualifications
        ]

    return _mutate(ctx, None, replace_all)


def record_submission(ctx: AppContext, data: RecordSubmissionInput) -> SubmissionOutput:
    """提出を記録する。snapshot を省略すると現在の SkillProfile 全体を固定して残す。"""
    with ctx.uow_factory() as uow:
        application = load_application(uow, data.application_id)
        if data.document_version_id is not None:
            if uow.documents.get_version(data.document_version_id) is None:
                raise NotFoundError(
                    "書類の版",
                    data.document_version_id,
                    "get_document で版の ID を確認してください。",
                )
        snapshot = data.snapshot
        if snapshot is None:
            profile = uow.skill_profile.get()
            snapshot = SkillProfileOutput.model_validate(profile).model_dump(mode="json")
        submission = Submission.record(
            application.id,
            data.submitted_at,
            data.kind,
            data.template_file_name,
            data.received_at,
            snapshot,
            data.document_version_id,
            data.memo,
        )
        uow.submissions.add(submission)
        uow.commit()
        return SubmissionOutput.model_validate(submission)


def list_submissions(ctx: AppContext, data: ListSubmissionsInput) -> Page[SubmissionOutput]:
    """提出記録を snapshot なしで一覧する。"""
    with ctx.uow_factory() as uow:
        items, total = uow.submissions.search(data.application_id, data.limit, data.offset)
        return Page(
            items=[SubmissionOutput.model_validate(s) for s in items],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )


def get_submission(ctx: AppContext, data: GetSubmissionInput) -> SubmissionDetail:
    """提出記録を snapshot つきで取得する。"""
    with ctx.uow_factory() as uow:
        submission = uow.submissions.get(data.submission_id)
        if submission is None:
            raise NotFoundError(
                "提出記録", data.submission_id, "list_submissions で ID を確認してください。"
            )
        return SubmissionDetail.model_validate(submission)
