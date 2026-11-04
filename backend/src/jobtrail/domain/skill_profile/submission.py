from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from jobtrail.domain.shared.ids import (
    ApplicationId,
    DocumentVersionId,
    SubmissionId,
    new_id,
)


class SubmissionKind(StrEnum):
    SKILL_SHEET = "skill_sheet"
    CAREER_HISTORY = "career_history"
    RESUME = "resume"
    OTHER = "other"


@dataclass(eq=False)
class Submission:
    """提出の記録。ファイル本体は持たず、提出時点の内容を snapshot として固定する。"""

    id: SubmissionId
    application_id: ApplicationId
    submitted_at: datetime
    kind: SubmissionKind
    template_file_name: str | None
    received_at: datetime | None
    snapshot: dict[str, Any]
    document_version_id: DocumentVersionId | None
    memo: str

    @classmethod
    def record(
        cls,
        application_id: ApplicationId,
        submitted_at: datetime,
        kind: SubmissionKind,
        template_file_name: str | None,
        received_at: datetime | None,
        snapshot: dict[str, Any],
        document_version_id: DocumentVersionId | None,
        memo: str,
    ) -> "Submission":
        return cls(
            id=new_id(),
            application_id=application_id,
            submitted_at=submitted_at,
            kind=kind,
            template_file_name=template_file_name,
            received_at=received_at,
            snapshot=snapshot,
            document_version_id=document_version_id,
            memo=memo,
        )
