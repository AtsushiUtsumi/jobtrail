import json
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from jobtrail.domain.shared.errors import ConflictError
from jobtrail.domain.shared.ids import ApplicationId, SubmissionId
from jobtrail.domain.skill_profile.skill_profile import (
    Basic,
    Career,
    Disclosure,
    Project,
    Qualification,
    Skill,
    SkillProfile,
)
from jobtrail.domain.skill_profile.submission import Submission
from jobtrail.infra.db.models import skill_profiles, submissions

_SINGLETON_ID = UUID(int=1)


def _to_json(profile: SkillProfile) -> dict[str, Any]:
    data = asdict(profile)
    del data["version"], data["updated_at"]
    encoded: dict[str, Any] = json.loads(json.dumps(data, default=str))
    return encoded


def _with_id(item: dict[str, Any]) -> dict[str, Any]:
    return {**item, "id": UUID(item["id"])}


def _from_row(row: sa.RowMapping) -> SkillProfile:
    data = row["data"]
    return SkillProfile(
        basic=Basic(**data.get("basic", {})),
        careers=[Career(**_with_id(c)) for c in data.get("careers", [])],
        projects=[
            Project(**{**_with_id(p), "disclosure": Disclosure(p["disclosure"])})
            for p in data.get("projects", [])
        ],
        skills=[Skill(**_with_id(s)) for s in data.get("skills", [])],
        qualifications=[Qualification(**_with_id(q)) for q in data.get("qualifications", [])],
        version=row["version"],
        updated_at=row["updated_at"],
    )


class SqlSkillProfileRepository:
    """入れ子の値を 1 行の JSONB に保存し、version で楽観ロックする。"""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self) -> SkillProfile:
        self._session.execute(
            insert(skill_profiles)
            .values(id=_SINGLETON_ID, data=_to_json(SkillProfile()), version=1)
            .on_conflict_do_nothing()
        )
        row = self._session.execute(sa.select(skill_profiles)).mappings().one()
        return _from_row(row)

    def save(self, profile: SkillProfile) -> None:
        result = self._session.execute(
            sa.update(skill_profiles)
            .where(
                skill_profiles.c.id == _SINGLETON_ID,
                skill_profiles.c.version == profile.version,
            )
            .values(
                data=_to_json(profile),
                version=profile.version + 1,
                updated_at=profile.updated_at,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise ConflictError()
        profile.version += 1


class SqlSubmissionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, submission: Submission) -> None:
        self._session.add(submission)

    def get(self, submission_id: SubmissionId) -> Submission | None:
        return self._session.get(Submission, submission_id)

    def search(
        self, application_id: ApplicationId | None, limit: int, offset: int
    ) -> tuple[Sequence[Submission], int]:
        conditions = (
            [submissions.c.application_id == application_id] if application_id is not None else []
        )
        total = self._session.scalar(
            sa.select(sa.func.count()).select_from(submissions).where(*conditions)
        )
        items = self._session.scalars(
            sa.select(Submission)
            .where(*conditions)
            .order_by(submissions.c.submitted_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return items, total or 0
