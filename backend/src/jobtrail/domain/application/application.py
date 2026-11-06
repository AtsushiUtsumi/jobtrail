from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Protocol

from jobtrail.domain.application.stage import Stage, StageResult, StageType
from jobtrail.domain.application.value_objects import (
    ApplicationChannel,
    ApplicationStatus,
    Outcome,
)
from jobtrail.domain.shared.errors import DomainError, ErrorKind, NotFoundError
from jobtrail.domain.shared.ids import ApplicationId, CompanyId, DocumentVersionId, StageId, new_id

DEFAULT_PRIORITY = 50

_STATUS_BY_OUTCOME = {
    Outcome.REJECTED: ApplicationStatus.REJECTED,
    Outcome.OFFER_ACCEPTED: ApplicationStatus.OFFER_ACCEPTED,
    Outcome.OFFER_DECLINED: ApplicationStatus.OFFER_DECLINED,
    Outcome.WITHDRAWN: ApplicationStatus.WITHDRAWN,
}


class StageLike(Protocol):
    @property
    def type(self) -> StageType: ...

    @property
    def result(self) -> StageResult: ...


@dataclass(frozen=True)
class DerivedStatus:
    status: ApplicationStatus
    stage_type: StageType | None = None
    outcome: Outcome = Outcome.IN_PROGRESS


def derive_status(
    outcome: Outcome, applied_at: datetime | None, stages: Sequence[StageLike]
) -> DerivedStatus:
    """status は保存せず、常にこの関数で導出する（集約と読み取りモデルで共有）。"""
    if outcome is not Outcome.IN_PROGRESS:
        last_type = stages[-1].type if stages else None
        status = _STATUS_BY_OUTCOME.get(outcome, ApplicationStatus.CLOSED)
        return DerivedStatus(status, last_type, outcome)
    if applied_at is None:
        return DerivedStatus(ApplicationStatus.CONSIDERING)
    if not stages:
        return DerivedStatus(ApplicationStatus.DOCUMENT)
    last_type = stages[-1].type
    return DerivedStatus(ApplicationStatus(last_type.value), last_type)


@dataclass(eq=False)
class Application:
    id: ApplicationId
    company_id: CompanyId
    position: str
    channel: ApplicationChannel
    agent_name: str | None
    applied_at: datetime | None
    outcome: Outcome
    submitted_document_version_id: DocumentVersionId | None
    memo: str
    created_at: datetime
    updated_at: datetime
    stages: list[Stage] = field(default_factory=list)
    version: int = 0
    priority: int = DEFAULT_PRIORITY

    @classmethod
    def consider(
        cls,
        company_id: CompanyId,
        position: str,
        channel: ApplicationChannel,
        agent_name: str | None,
        memo: str,
        now: datetime,
        priority: int = DEFAULT_PRIORITY,
    ) -> "Application":
        """初期状態は検討中（stages も applied_at も空）。"""
        return cls(
            id=new_id(),
            company_id=company_id,
            position=position,
            channel=channel,
            agent_name=agent_name,
            applied_at=None,
            outcome=Outcome.IN_PROGRESS,
            submitted_document_version_id=None,
            priority=priority,
            memo=memo,
            created_at=now,
            updated_at=now,
        )

    @property
    def derived_status(self) -> DerivedStatus:
        return derive_status(self.outcome, self.applied_at, self.stages)

    @property
    def is_closed(self) -> bool:
        return self.outcome is not Outcome.IN_PROGRESS

    @property
    def is_considering(self) -> bool:
        return self.applied_at is None and not self.is_closed

    def apply(self, applied_at: datetime, now: datetime) -> None:
        self._ensure_open()
        if self.applied_at is not None:
            raise DomainError(
                "ALREADY_APPLIED",
                "この応募は既に応募済みです。",
                "選考を進めるには advance_stage を使ってください。",
            )
        self.applied_at = applied_at
        self.updated_at = now

    def add_stage(
        self,
        type: StageType,
        label: str | None,
        scheduled_at: datetime | None,
        memo: str,
        now: datetime,
    ) -> Stage:
        self._ensure_open()
        if self.applied_at is None:
            raise DomainError(
                "NOT_APPLIED_YET",
                "検討中の応募には Stage を追加できません。",
                "先に apply で応募日を記録してください。",
            )
        if self.stages:
            last = self.stages[-1]
            if last.result is StageResult.PENDING:
                raise DomainError(
                    "STAGE_PENDING_RESULT",
                    "直前の Stage の結果が未確定です。",
                    "直前の Stage の結果を record_stage_result で記録してください。",
                    details={"stage_id": str(last.id)},
                )
            if last.result.is_terminal:
                raise DomainError(
                    "STAGE_TERMINATED",
                    "不合格・辞退の Stage の後ろには Stage を追加できません。",
                    "選考を再開する場合は reopen_application を使ってください。",
                )
        stage = Stage.new(type, label, scheduled_at, memo, len(self.stages), now)
        self.stages.append(stage)
        self.updated_at = now
        return stage

    def record_stage_result(
        self, stage_id: StageId, result: StageResult, memo: str | None, now: datetime
    ) -> None:
        """結果の記録と訂正は最新の Stage にのみ行える（途中に不合格を残さないため）。"""
        self._ensure_open()
        stage = self._stage(stage_id)
        if stage is not self.stages[-1]:
            raise DomainError(
                "STAGE_NOT_LATEST",
                "最新ではない Stage の結果は変更できません。",
                "最新の Stage に対して record_stage_result を実行してください。",
                details={"latest_stage_id": str(self.stages[-1].id)},
            )
        stage.result = result
        stage.result_recorded_at = None if result is StageResult.PENDING else now
        if memo is not None:
            stage.memo = memo
        self.updated_at = now
        if result is StageResult.REJECTED:
            self.outcome = Outcome.REJECTED
        elif result is StageResult.DECLINED:
            self.outcome = Outcome.WITHDRAWN

    def reschedule_stage(
        self, stage_id: StageId, scheduled_at: datetime | None, now: datetime
    ) -> None:
        self._ensure_open()
        self._stage(stage_id).scheduled_at = scheduled_at
        self.updated_at = now

    def update_stage_memo(self, stage_id: StageId, memo: str, now: datetime) -> None:
        self._ensure_open()
        self._stage(stage_id).memo = memo
        self.updated_at = now

    def close(self, outcome: Outcome, now: datetime) -> None:
        self._ensure_open()
        if outcome is Outcome.IN_PROGRESS:
            raise DomainError(
                "INVALID_OUTCOME",
                "close_application に in_progress は指定できません。",
                "終了理由となる outcome を指定してください。",
                ErrorKind.INVALID,
            )
        if outcome is Outcome.PASSED_OVER and not self.is_considering:
            raise DomainError(
                "NOT_CONSIDERING",
                "見送りは検討中の応募にのみ指定できます。",
                "応募後の終了には withdrawn（応募辞退）などを指定してください。",
            )
        if self.is_considering and outcome not in (Outcome.PASSED_OVER, Outcome.POSTING_CLOSED):
            raise DomainError(
                "NOT_APPLIED_YET",
                "検討中の応募に指定できる終了理由は見送りと募集終了のみです。",
                "passed_over か posting_closed を指定するか、先に apply を実行してください。",
            )
        self.outcome = outcome
        self.updated_at = now

    def reopen(self, now: datetime) -> None:
        """終了を取り消す。最後の不合格・辞退は結果待ちへ戻し、選考を続けられる状態にする。"""
        if not self.is_closed:
            raise DomainError(
                "APPLICATION_NOT_CLOSED",
                "この応募は終了していません。",
                "reopen_application は終了した応募にのみ使えます。",
            )
        self.outcome = Outcome.IN_PROGRESS
        if self.stages and self.stages[-1].result.is_terminal:
            self.stages[-1].result = StageResult.PENDING
            self.stages[-1].result_recorded_at = None
        self.updated_at = now

    def update_details(self, now: datetime, **changes: Any) -> None:
        for name in ("position", "channel", "agent_name", "priority", "memo"):
            if name in changes:
                setattr(self, name, changes[name])
        self.updated_at = now

    def attach_submitted_document(self, version_id: DocumentVersionId, now: datetime) -> None:
        self._ensure_open()
        self.submitted_document_version_id = version_id
        self.updated_at = now

    def _ensure_open(self) -> None:
        if self.is_closed:
            raise DomainError(
                "APPLICATION_CLOSED",
                f"この応募は終了しています（{self.outcome.value}）。",
                "変更するには先に reopen_application で再開してください。",
            )

    def _stage(self, stage_id: StageId) -> Stage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise NotFoundError(
            "Stage", stage_id, "get_application で Stage の ID を確認してください。"
        )
