from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from jobtrail.domain.shared.ids import StageId, new_id


class StageType(StrEnum):
    CASUAL = "casual"
    DOCUMENT = "document"
    FIRST_INTERVIEW = "first_interview"
    SECOND_INTERVIEW = "second_interview"
    OFFER = "offer"


class StageResult(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    REJECTED = "rejected"
    DECLINED = "declined"

    @property
    def is_terminal(self) -> bool:
        return self in (StageResult.REJECTED, StageResult.DECLINED)


@dataclass(eq=False)
class Stage:
    id: StageId
    type: StageType
    label: str | None
    scheduled_at: datetime | None
    result: StageResult
    memo: str
    position: int
    created_at: datetime
    result_recorded_at: datetime | None = None

    @classmethod
    def new(
        cls,
        type: StageType,
        label: str | None,
        scheduled_at: datetime | None,
        memo: str,
        position: int,
        now: datetime,
    ) -> "Stage":
        return cls(
            id=new_id(),
            type=type,
            label=label,
            scheduled_at=scheduled_at,
            result=StageResult.PENDING,
            memo=memo,
            position=position,
            created_at=now,
        )
