from collections.abc import Sequence
from typing import Protocol

from jobtrail.domain.shared.ids import ApplicationId, SubmissionId
from jobtrail.domain.skill_profile.skill_profile import SkillProfile
from jobtrail.domain.skill_profile.submission import Submission


class SkillProfileRepository(Protocol):
    def get(self) -> SkillProfile:
        """唯一の SkillProfile を返す（未作成なら作成する）。"""
        ...

    def save(self, profile: SkillProfile) -> None:
        """profile.version を WHERE 条件に更新し、version を進める。"""
        ...


class SubmissionRepository(Protocol):
    def add(self, submission: Submission) -> None: ...

    def get(self, submission_id: SubmissionId) -> Submission | None: ...

    def search(
        self, application_id: ApplicationId | None, limit: int, offset: int
    ) -> tuple[Sequence[Submission], int]: ...
