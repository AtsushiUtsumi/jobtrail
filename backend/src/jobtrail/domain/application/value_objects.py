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
    CASUAL = "casual"
    DOCUMENT = "document"
    FIRST_INTERVIEW = "first_interview"
    SECOND_INTERVIEW = "second_interview"
    OFFER = "offer"
    REJECTED = "rejected"
    OFFER_ACCEPTED = "offer_accepted"
    OFFER_DECLINED = "offer_declined"
    WITHDRAWN = "withdrawn"
    CLOSED = "closed"

    @property
    def is_closed(self) -> bool:
        return self in (
            ApplicationStatus.REJECTED,
            ApplicationStatus.OFFER_ACCEPTED,
            ApplicationStatus.OFFER_DECLINED,
            ApplicationStatus.WITHDRAWN,
            ApplicationStatus.CLOSED,
        )


@dataclass(frozen=True)
class SalaryRange:
    minimum: int | None = None
    maximum: int | None = None
    currency: str = "JPY"
    period: str = "year"
