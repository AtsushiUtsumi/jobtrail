from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from jobtrail.domain.application.application import Application, derive_status
from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import (
    ApplicationChannel,
    ApplicationStatus,
    Outcome,
)
from jobtrail.domain.shared.errors import DomainError, ErrorKind, NotFoundError

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def considering() -> Application:
    return Application.consider(uuid4(), "SWE", ApplicationChannel.DIRECT, None, "", NOW)


def applied() -> Application:
    application = considering()
    application.apply(NOW, NOW)
    return application


def in_stage(type: StageType = StageType.DOCUMENT) -> Application:
    application = applied()
    application.add_stage(type, None, None, "", NOW)
    return application


def after_result(result: StageResult, type: StageType = StageType.DOCUMENT) -> Application:
    application = in_stage(type)
    application.record_stage_result(application.stages[-1].id, result, None, NOW)
    return application


def closed(outcome: Outcome = Outcome.WITHDRAWN) -> Application:
    application = applied()
    application.close(outcome, NOW)
    return application


def assert_error(code: str, action: Callable[[], object]) -> None:
    with pytest.raises(DomainError) as info:
        action()
    assert info.value.code == code
    assert info.value.hint


class TestStatusDerivation:
    def test_initial_state_is_considering(self) -> None:
        application = considering()
        assert application.stages == []
        assert application.applied_at is None
        assert application.derived_status.status is ApplicationStatus.CONSIDERING

    def test_applied_without_stages(self) -> None:
        assert applied().derived_status.status is ApplicationStatus.APPLIED

    def test_pending_stage_is_in_stage_with_type(self) -> None:
        derived = in_stage(StageType.INTERVIEW).derived_status
        assert derived.status is ApplicationStatus.IN_STAGE
        assert derived.stage_type is StageType.INTERVIEW

    def test_passed_stage_awaits_next(self) -> None:
        derived = after_result(StageResult.PASSED).derived_status
        assert derived.status is ApplicationStatus.AWAITING_NEXT_STAGE

    def test_passed_offer_stage_is_offer_pending(self) -> None:
        derived = after_result(StageResult.PASSED, StageType.OFFER).derived_status
        assert derived.status is ApplicationStatus.OFFER_PENDING

    @pytest.mark.parametrize(
        "outcome", [o for o in Outcome if o not in (Outcome.IN_PROGRESS, Outcome.PASSED_OVER)]
    )
    def test_closed_exposes_outcome(self, outcome: Outcome) -> None:
        derived = closed(outcome).derived_status
        assert derived.status is ApplicationStatus.CLOSED
        assert derived.outcome is outcome

    def test_passed_over_is_closed(self) -> None:
        application = considering()
        application.close(Outcome.PASSED_OVER, NOW)
        assert application.derived_status.outcome is Outcome.PASSED_OVER

    def test_outcome_takes_precedence_over_everything(self) -> None:
        derived = derive_status(Outcome.REJECTED, None, [])
        assert derived.status is ApplicationStatus.CLOSED


class TestApply:
    def test_records_applied_at(self) -> None:
        application = considering()
        applied_at = NOW + timedelta(days=1)
        application.apply(applied_at, NOW)
        assert application.applied_at == applied_at

    def test_rejects_second_apply(self) -> None:
        application = applied()
        assert_error("ALREADY_APPLIED", lambda: application.apply(NOW, NOW))

    def test_rejects_when_closed(self) -> None:
        application = considering()
        application.close(Outcome.PASSED_OVER, NOW)
        assert_error("APPLICATION_CLOSED", lambda: application.apply(NOW, NOW))


class TestAddStage:
    def test_rejects_while_considering(self) -> None:
        application = considering()
        assert_error(
            "NOT_APPLIED_YET",
            lambda: application.add_stage(StageType.DOCUMENT, None, None, "", NOW),
        )

    def test_rejects_while_previous_is_pending(self) -> None:
        application = in_stage()
        assert_error(
            "STAGE_PENDING_RESULT",
            lambda: application.add_stage(StageType.INTERVIEW, None, None, "", NOW),
        )

    @pytest.mark.parametrize("result", [StageResult.REJECTED, StageResult.DECLINED])
    def test_rejects_after_terminal_result_even_when_outcome_was_cleared(
        self, result: StageResult
    ) -> None:
        application = after_result(result)
        application.outcome = Outcome.IN_PROGRESS
        assert_error(
            "STAGE_TERMINATED",
            lambda: application.add_stage(StageType.INTERVIEW, None, None, "", NOW),
        )

    def test_rejects_when_closed(self) -> None:
        application = closed()
        assert_error(
            "APPLICATION_CLOSED",
            lambda: application.add_stage(StageType.DOCUMENT, None, None, "", NOW),
        )

    def test_order_of_types_is_free(self) -> None:
        application = after_result(StageResult.PASSED, StageType.FINAL)
        stage = application.add_stage(StageType.CASUAL, "2 回目", None, "", NOW)
        assert stage.position == 1
        assert [s.type for s in application.stages] == [StageType.FINAL, StageType.CASUAL]


class TestRecordStageResult:
    def test_rejected_closes_application(self) -> None:
        assert after_result(StageResult.REJECTED).outcome is Outcome.REJECTED

    def test_declined_closes_application_as_withdrawn(self) -> None:
        assert after_result(StageResult.DECLINED).outcome is Outcome.WITHDRAWN

    def test_passed_keeps_application_open(self) -> None:
        assert after_result(StageResult.PASSED).outcome is Outcome.IN_PROGRESS

    def test_records_memo_and_time(self) -> None:
        application = in_stage()
        stage = application.stages[0]
        application.record_stage_result(stage.id, StageResult.PASSED, "良い感触", NOW)
        assert stage.memo == "良い感触"
        assert stage.result_recorded_at == NOW

    def test_back_to_pending_clears_recorded_time(self) -> None:
        application = after_result(StageResult.PASSED)
        stage = application.stages[0]
        application.record_stage_result(stage.id, StageResult.PENDING, None, NOW)
        assert stage.result_recorded_at is None

    def test_rejects_non_latest_stage(self) -> None:
        application = after_result(StageResult.PASSED)
        first = application.stages[0]
        application.add_stage(StageType.INTERVIEW, None, None, "", NOW)
        assert_error(
            "STAGE_NOT_LATEST",
            lambda: application.record_stage_result(first.id, StageResult.REJECTED, None, NOW),
        )

    def test_rejects_unknown_stage(self) -> None:
        application = in_stage()
        with pytest.raises(NotFoundError):
            application.record_stage_result(uuid4(), StageResult.PASSED, None, NOW)

    def test_rejects_when_closed(self) -> None:
        application = after_result(StageResult.REJECTED)
        stage = application.stages[0]
        assert_error(
            "APPLICATION_CLOSED",
            lambda: application.record_stage_result(stage.id, StageResult.PASSED, None, NOW),
        )


class TestStageChangesWhenClosed:
    def test_reschedule_rejected(self) -> None:
        application = after_result(StageResult.REJECTED)
        stage = application.stages[0]
        assert_error("APPLICATION_CLOSED", lambda: application.reschedule_stage(stage.id, NOW, NOW))

    def test_memo_rejected(self) -> None:
        application = after_result(StageResult.REJECTED)
        stage = application.stages[0]
        assert_error(
            "APPLICATION_CLOSED", lambda: application.update_stage_memo(stage.id, "x", NOW)
        )

    def test_reschedule_and_memo_allowed_while_open(self) -> None:
        application = in_stage()
        stage = application.stages[0]
        application.reschedule_stage(stage.id, NOW, NOW)
        application.update_stage_memo(stage.id, "質問", NOW)
        assert stage.scheduled_at == NOW
        assert stage.memo == "質問"


class TestClose:
    def test_rejects_in_progress(self) -> None:
        application = applied()
        with pytest.raises(DomainError) as info:
            application.close(Outcome.IN_PROGRESS, NOW)
        assert info.value.kind is ErrorKind.INVALID

    @pytest.mark.parametrize("build", [applied, in_stage])
    def test_passed_over_only_from_considering(self, build: Callable[[], Application]) -> None:
        application = build()
        assert_error("NOT_CONSIDERING", lambda: application.close(Outcome.PASSED_OVER, NOW))

    def test_posting_closed_allowed_from_considering(self) -> None:
        application = considering()
        application.close(Outcome.POSTING_CLOSED, NOW)
        assert application.outcome is Outcome.POSTING_CLOSED

    @pytest.mark.parametrize(
        "outcome",
        [Outcome.REJECTED, Outcome.WITHDRAWN, Outcome.OFFER_ACCEPTED, Outcome.OFFER_DECLINED],
    )
    def test_applied_outcomes_rejected_from_considering(self, outcome: Outcome) -> None:
        application = considering()
        assert_error("NOT_APPLIED_YET", lambda: application.close(outcome, NOW))

    def test_rejects_double_close(self) -> None:
        application = closed()
        assert_error("APPLICATION_CLOSED", lambda: application.close(Outcome.REJECTED, NOW))


class TestReopen:
    def test_reopens_closed_application(self) -> None:
        application = closed()
        application.reopen(NOW)
        assert application.outcome is Outcome.IN_PROGRESS
        assert application.derived_status.status is ApplicationStatus.APPLIED

    def test_terminal_stage_returns_to_pending(self) -> None:
        application = after_result(StageResult.REJECTED)
        application.reopen(NOW)
        assert application.stages[-1].result is StageResult.PENDING
        assert application.stages[-1].result_recorded_at is None
        assert application.derived_status.status is ApplicationStatus.IN_STAGE

    def test_rejects_when_not_closed(self) -> None:
        application = applied()
        assert_error("APPLICATION_NOT_CLOSED", lambda: application.reopen(NOW))


class TestDetails:
    def test_partial_update_only_touches_given_fields(self) -> None:
        application = considering()
        application.update_details(NOW, memo="メモ")
        assert application.memo == "メモ"
        assert application.position == "SWE"

    def test_details_can_be_updated_when_closed(self) -> None:
        application = closed()
        application.update_details(NOW, memo="振り返り")
        assert application.memo == "振り返り"

    def test_attach_document(self) -> None:
        application = applied()
        version_id = uuid4()
        application.attach_submitted_document(version_id, NOW)
        assert application.submitted_document_version_id == version_id

    def test_attach_document_rejected_when_closed(self) -> None:
        application = closed()
        assert_error(
            "APPLICATION_CLOSED", lambda: application.attach_submitted_document(uuid4(), NOW)
        )
