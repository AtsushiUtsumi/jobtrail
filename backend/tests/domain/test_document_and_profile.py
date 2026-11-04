from dataclasses import fields
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from jobtrail.domain.document.document import Document, DocumentKind, DocumentVersion
from jobtrail.domain.shared.errors import NotFoundError
from jobtrail.domain.skill_profile.skill_profile import (
    Basic,
    Career,
    Disclosure,
    Project,
    Skill,
    SkillProfile,
    add_item,
    remove_item,
    update_item,
)

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def test_document_versions_are_numbered() -> None:
    document = Document.create("職務経歴書", DocumentKind.CAREER_HISTORY, NOW)
    first = document.add_version("# v1", "", NOW)
    second = document.add_version("# v2", "修正", NOW)
    assert (first.number, second.number) == (1, 2)
    assert document.versions == [first, second]


def test_document_has_no_operation_to_edit_a_version() -> None:
    mutators = [name for name in vars(Document) if "edit" in name or "update" in name]
    assert mutators == []
    assert not [name for name in vars(DocumentVersion) if name.startswith(("set_", "update"))]


def profile() -> SkillProfile:
    target = SkillProfile()
    add_item(
        target.projects,
        Project,
        summary="決済基盤",
        end="2025-03",
        languages=["Python"],
        disclosure=Disclosure.ANONYMIZED,
    )
    add_item(target.projects, Project, summary="社内ツール", end="2015-01", languages=["Java"])
    add_item(target.projects, Project, summary="現行案件", frameworks=["FastAPI"])
    add_item(target.skills, Skill, name="Python")
    add_item(target.skills, Skill, name="Java")
    return target


def test_new_profile_is_empty() -> None:
    assert SkillProfile().is_empty
    assert not profile().is_empty


def test_basic_is_partially_updated() -> None:
    target = SkillProfile()
    target.update_basic(full_name="山田")
    target.update_basic(age=30)
    assert (target.basic.full_name, target.basic.age) == ("山田", 30)
    assert not target.is_empty
    assert {f.name for f in fields(Basic)} >= {"self_pr", "strengths_summary"}


def test_items_can_be_updated_and_removed() -> None:
    target = SkillProfile()
    career = add_item(target.careers, Career, company_name="A社")
    updated = update_item(target.careers, career.id, role="SE")
    assert (updated.id, updated.company_name, updated.role) == (career.id, "A社", "SE")
    remove_item(target.careers, career.id)
    assert target.careers == []


def test_unknown_item_is_not_found() -> None:
    with pytest.raises(NotFoundError):
        update_item(SkillProfile().careers, uuid4(), role="SE")
    with pytest.raises(NotFoundError):
        remove_item(SkillProfile().careers, uuid4())


def test_filter_by_technology_is_case_insensitive() -> None:
    result = profile().filtered("python", None, None, date(2026, 1, 1))
    assert [p.summary for p in result.projects] == ["決済基盤"]
    assert [s.name for s in result.skills] == ["Python"]


def test_filter_by_recent_years_keeps_ongoing() -> None:
    result = profile().filtered(None, 3, None, date(2026, 1, 1))
    assert [p.summary for p in result.projects] == ["決済基盤", "現行案件"]


def test_filter_by_disclosure() -> None:
    result = profile().filtered(None, None, Disclosure.ANONYMIZED, date(2026, 1, 1))
    assert [p.summary for p in result.projects] == ["決済基盤"]


def test_filter_does_not_change_the_original() -> None:
    target = profile()
    target.filtered("python", None, None, date(2026, 1, 1))
    assert len(target.projects) == 3
