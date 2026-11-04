from dataclasses import dataclass, field, replace
from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from jobtrail.domain.shared.errors import NotFoundError
from jobtrail.domain.shared.ids import new_id


class Disclosure(StrEnum):
    PUBLIC = "public"
    ANONYMIZED = "anonymized"
    PRIVATE = "private"


@dataclass
class Basic:
    full_name: str = ""
    birth_date: str | None = None
    age: int | None = None
    nearest_station: str = ""
    desired_conditions: str = ""
    self_pr: str = ""
    strengths_summary: str = ""


@dataclass
class Career:
    id: UUID
    company_name: str
    start: str | None = None
    end: str | None = None
    employment_type: str = ""
    role: str = ""
    summary: str = ""


@dataclass
class Project:
    id: UUID
    summary: str
    start: str | None = None
    end: str | None = None
    role: str = ""
    team_size: int | None = None
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    databases: list[str] = field(default_factory=list)
    infrastructure: list[str] = field(default_factory=list)
    phases: list[str] = field(default_factory=list)
    achievements: str = ""
    disclosure: Disclosure = Disclosure.PUBLIC
    anonymized_name: str | None = None

    @property
    def technologies(self) -> list[str]:
        return self.languages + self.frameworks + self.databases + self.infrastructure

    def uses(self, technology: str) -> bool:
        needle = technology.casefold()
        return any(needle in name.casefold() for name in self.technologies)


@dataclass
class Skill:
    id: UUID
    name: str
    category: str = ""
    years: float | None = None
    proficiency: str = ""


@dataclass
class Qualification:
    id: UUID
    name: str
    acquired_on: str | None = None


def add_item[T: (Career, Project, Skill, Qualification)](
    items: list[T], factory: type[T], **values: Any
) -> T:
    item = factory(id=new_id(), **values)
    items.append(item)
    return item


def update_item[T: (Career, Project, Skill, Qualification)](
    items: list[T], item_id: UUID, **changes: Any
) -> T:
    index = _locate(items, item_id)
    items[index] = replace(items[index], **changes)
    return items[index]


def remove_item[T: (Career, Project, Skill, Qualification)](items: list[T], item_id: UUID) -> None:
    del items[_locate(items, item_id)]


def _locate[T: (Career, Project, Skill, Qualification)](items: list[T], item_id: UUID) -> int:
    for index, item in enumerate(items):
        if item.id == item_id:
            return index
    raise NotFoundError(
        "SkillProfile の要素", item_id, "get_skill_profile で要素の ID を確認してください。"
    )


@dataclass
class SkillProfile:
    """1 インスタンスに 1 つ。Document とは別集約の構造化データ。"""

    basic: Basic = field(default_factory=Basic)
    careers: list[Career] = field(default_factory=list)
    projects: list[Project] = field(default_factory=list)
    skills: list[Skill] = field(default_factory=list)
    qualifications: list[Qualification] = field(default_factory=list)
    version: int = 0
    updated_at: datetime | None = None

    @property
    def is_empty(self) -> bool:
        return not (
            self.careers
            or self.projects
            or self.skills
            or self.qualifications
            or self.basic != Basic()
        )

    def update_basic(self, **changes: Any) -> None:
        self.basic = replace(self.basic, **changes)

    def filtered(
        self,
        technology: str | None,
        recent_years: int | None,
        disclosure: Disclosure | None,
        today: date,
    ) -> "SkillProfile":
        """条件に合う projects / skills だけを残した写しを返す。"""
        projects = self.projects
        skills = self.skills
        if technology:
            needle = technology.casefold()
            projects = [p for p in projects if p.uses(technology)]
            skills = [s for s in skills if needle in s.name.casefold()]
        if recent_years is not None:
            cutoff = f"{today.year - recent_years:04d}-{today.month:02d}"
            projects = [p for p in projects if p.end is None or p.end[:7] >= cutoff]
        if disclosure is not None:
            projects = [p for p in projects if p.disclosure is disclosure]
        return replace(self, projects=list(projects), skills=list(skills))
