from dataclasses import dataclass
from enum import StrEnum


class ApplicationChannel(StrEnum):
    DIRECT = "direct"
    AGENT = "agent"
    SCOUT = "scout"
    REFERRAL = "referral"


class Outcome(StrEnum):
    IN_PROGRESS = "in_progress"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    POSTING_CLOSED = "posting_closed"
    PASSED_OVER = "passed_over"


class ApplicationStatus(StrEnum):
    CONSIDERING = "considering"
    APPLIED = "applied"
    IN_STAGE = "in_stage"
    AWAITING_NEXT_STAGE = "awaiting_next_stage"
    OFFER_PENDING = "offer_pending"
    CLOSED = "closed"


@dataclass(frozen=True)
class SalaryRange:
    minimum: int | None = None
    maximum: int | None = None
    currency: str = "JPY"
    period: str = "year"
