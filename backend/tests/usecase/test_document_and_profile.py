from uuid import uuid4

import pytest

from jobtrail.domain.document.document import DocumentKind
from jobtrail.domain.shared.errors import ConflictError, DomainError, NotFoundError
from jobtrail.domain.skill_profile.skill_profile import Disclosure
from jobtrail.schemas.application import GetApplicationInput
from jobtrail.schemas.document import (
    AddDocumentVersionInput,
    AttachDocumentInput,
    CreateDocumentInput,
    GetDocumentInput,
    ListDocumentsInput,
)
from jobtrail.schemas.skill_profile import (
    AddCareerInput,
    AddProjectInput,
    AddQualificationInput,
    AddSkillInput,
    BasicFields,
    CareerFields,
    GetSkillProfileInput,
    GetSubmissionInput,
    ImportSkillProfileInput,
    ListSubmissionsInput,
    ProjectFields,
    RecordSubmissionInput,
    RemoveCareerInput,
    RemoveProjectInput,
    RemoveQualificationInput,
    RemoveSkillInput,
    SkillFields,
    UpdateBasicInput,
    UpdateCareerInput,
    UpdateProjectInput,
    UpdateQualificationInput,
    UpdateSkillInput,
)
from jobtrail.usecase.application import commands as application
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.document import commands as document
from jobtrail.usecase.skill_profile import commands as profile
from tests.usecase.helpers import NOW, applied


def test_document_versions_accumulate(ctx: AppContext) -> None:
    created = document.create_document(
        ctx, CreateDocumentInput(name="職務経歴書", kind=DocumentKind.CAREER_HISTORY, body="# v1")
    )
    updated = document.add_document_version(
        ctx, AddDocumentVersionInput(document_id=created.id, body="# v2", note="修正")
    )
    assert [v.number for v in updated.versions] == [1, 2]
    assert updated.versions[0].body == "# v1"
    listed = document.list_documents(ctx, ListDocumentsInput())
    assert listed.items[0].latest_version_number == 2
    filtered = document.list_documents(ctx, ListDocumentsInput(kind=DocumentKind.RESUME))
    assert filtered.total == 0


def test_document_can_be_created_without_body(ctx: AppContext) -> None:
    created = document.create_document(
        ctx, CreateDocumentInput(name="履歴書", kind=DocumentKind.RESUME)
    )
    assert created.versions == []


def test_attached_version_is_marked_submitted(ctx: AppContext) -> None:
    target = applied(ctx)
    created = document.create_document(
        ctx, CreateDocumentInput(name="職務経歴書", kind=DocumentKind.CAREER_HISTORY, body="本文")
    )
    version = created.versions[0]
    assert version.submitted is False
    attached = document.attach_document_to_application(
        ctx, AttachDocumentInput(application_id=target.id, document_version_id=version.id)
    )
    assert attached.submitted_document_version_id == version.id
    fetched = document.get_document(ctx, GetDocumentInput(document_id=created.id))
    assert fetched.versions[0].submitted is True


def test_attach_unknown_version_is_not_found(ctx: AppContext) -> None:
    target = applied(ctx)
    with pytest.raises(NotFoundError):
        document.attach_document_to_application(
            ctx, AttachDocumentInput(application_id=target.id, document_version_id=uuid4())
        )


def test_profile_is_created_on_first_read(ctx: AppContext) -> None:
    first = profile.get_skill_profile(ctx, GetSkillProfileInput())
    assert first.version == 1
    assert first.careers == []


def test_items_have_ids_and_can_be_updated_individually(ctx: AppContext) -> None:
    result = profile.add_career(ctx, AddCareerInput(company_name="A社", start="2020-04"))
    career = result.careers[0]
    result = profile.update_career(ctx, UpdateCareerInput(career_id=career.id, role="SE"))
    assert (result.careers[0].company_name, result.careers[0].role) == ("A社", "SE")
    result = profile.update_career(ctx, UpdateCareerInput(career_id=career.id, start=None))
    assert result.careers[0].start is None
    result = profile.remove_career(ctx, RemoveCareerInput(career_id=career.id))
    assert result.careers == []


def test_every_section_round_trips(ctx: AppContext) -> None:
    result = profile.add_project(
        ctx,
        AddProjectInput(
            summary="決済基盤",
            languages=["Python"],
            disclosure=Disclosure.ANONYMIZED,
            anonymized_name="大手金融",
        ),
    )
    project_id = result.projects[0].id
    result = profile.update_project(ctx, UpdateProjectInput(project_id=project_id, team_size=8))
    assert result.projects[0].team_size == 8
    assert result.projects[0].disclosure is Disclosure.ANONYMIZED

    result = profile.add_skill(ctx, AddSkillInput(name="Python", years=5))
    skill_id = result.skills[0].id
    result = profile.update_skill(ctx, UpdateSkillInput(skill_id=skill_id, proficiency="上級"))
    assert result.skills[0].years == 5

    result = profile.add_qualification(ctx, AddQualificationInput(name="AWS SAA"))
    qualification_id = result.qualifications[0].id
    result = profile.update_qualification(
        ctx, UpdateQualificationInput(qualification_id=qualification_id, acquired_on="2024-05")
    )
    assert result.qualifications[0].acquired_on == "2024-05"

    result = profile.update_skill_profile_basic(ctx, UpdateBasicInput(full_name="山田太郎"))
    assert result.basic.full_name == "山田太郎"

    stored = profile.get_skill_profile(ctx, GetSkillProfileInput())
    assert stored.model_dump() == result.model_dump()

    profile.remove_project(ctx, RemoveProjectInput(project_id=project_id))
    profile.remove_skill(ctx, RemoveSkillInput(skill_id=skill_id))
    final = profile.remove_qualification(
        ctx, RemoveQualificationInput(qualification_id=qualification_id)
    )
    assert (final.projects, final.skills, final.qualifications) == ([], [], [])


def test_get_filters(ctx: AppContext) -> None:
    profile.add_project(ctx, AddProjectInput(summary="A", languages=["Python"], end="2010-01"))
    profile.add_project(ctx, AddProjectInput(summary="B", languages=["Go"]))
    by_tech = profile.get_skill_profile(ctx, GetSkillProfileInput(technology="python"))
    assert [p.summary for p in by_tech.projects] == ["A"]
    recent = profile.get_skill_profile(ctx, GetSkillProfileInput(recent_years=3))
    assert [p.summary for p in recent.projects] == ["B"]


def test_optimistic_lock(ctx: AppContext) -> None:
    current = profile.get_skill_profile(ctx, GetSkillProfileInput())
    profile.add_skill(ctx, AddSkillInput(name="Go", expected_version=current.version))
    with pytest.raises(ConflictError):
        profile.add_skill(ctx, AddSkillInput(name="Rust", expected_version=current.version))


def test_import_refuses_to_overwrite_without_consent(ctx: AppContext) -> None:
    payload = {
        "basic": BasicFields(full_name="山田"),
        "careers": [CareerFields(company_name="A社")],
        "projects": [ProjectFields(summary="案件", languages=["Python"])],
        "skills": [SkillFields(name="Python")],
    }
    imported = profile.import_skill_profile(ctx, ImportSkillProfileInput(**payload))
    assert imported.projects[0].id is not None

    with pytest.raises(DomainError) as info:
        profile.import_skill_profile(ctx, ImportSkillProfileInput(**payload))
    assert info.value.code == "SKILL_PROFILE_NOT_EMPTY"

    replaced = profile.import_skill_profile(
        ctx, ImportSkillProfileInput(basic=BasicFields(full_name="鈴木"), overwrite=True)
    )
    assert replaced.basic.full_name == "鈴木"
    assert replaced.careers == []


def test_submission_snapshot_is_frozen_at_submission_time(ctx: AppContext) -> None:
    target = applied(ctx)
    profile.add_skill(ctx, AddSkillInput(name="Python"))
    recorded = profile.record_submission(
        ctx,
        RecordSubmissionInput(
            application_id=target.id, submitted_at=NOW, template_file_name="様式A.xlsx"
        ),
    )
    profile.add_skill(ctx, AddSkillInput(name="Go"))

    detail = profile.get_submission(ctx, GetSubmissionInput(submission_id=recorded.id))
    assert [s["name"] for s in detail.snapshot["skills"]] == ["Python"]
    assert detail.template_file_name == "様式A.xlsx"
    listed = profile.list_submissions(ctx, ListSubmissionsInput(application_id=target.id))
    assert listed.total == 1
    assert profile.list_submissions(ctx, ListSubmissionsInput(application_id=uuid4())).total == 0
    fetched = application.get_application(ctx, GetApplicationInput(application_id=target.id))
    assert [s.id for s in fetched.submissions] == [recorded.id]


def test_submission_accepts_explicit_snapshot(ctx: AppContext) -> None:
    target = applied(ctx)
    recorded = profile.record_submission(
        ctx,
        RecordSubmissionInput(
            application_id=target.id, submitted_at=NOW, snapshot={"projects": ["匿名化済み"]}
        ),
    )
    detail = profile.get_submission(ctx, GetSubmissionInput(submission_id=recorded.id))
    assert detail.snapshot == {"projects": ["匿名化済み"]}


def test_submission_marks_document_version_as_submitted(ctx: AppContext) -> None:
    target = applied(ctx)
    created = document.create_document(
        ctx, CreateDocumentInput(name="経歴", kind=DocumentKind.CAREER_HISTORY, body="本文")
    )
    profile.record_submission(
        ctx,
        RecordSubmissionInput(
            application_id=target.id,
            submitted_at=NOW,
            document_version_id=created.versions[0].id,
        ),
    )
    fetched = document.get_document(ctx, GetDocumentInput(document_id=created.id))
    assert fetched.versions[0].submitted is True


def test_submission_with_unknown_document_is_rejected(ctx: AppContext) -> None:
    target = applied(ctx)
    with pytest.raises(NotFoundError):
        profile.record_submission(
            ctx,
            RecordSubmissionInput(
                application_id=target.id, submitted_at=NOW, document_version_id=uuid4()
            ),
        )
