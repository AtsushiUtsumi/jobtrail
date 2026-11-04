from datetime import datetime
from statistics import mean, median

from jobtrail.domain.application.repository import ApplicationRow
from jobtrail.domain.application.stage import StageResult, StageType
from jobtrail.domain.application.value_objects import ApplicationChannel, Outcome
from jobtrail.schemas.analytics import (
    ChannelStats,
    DaysToOffer,
    StagePassRate,
    StatsOutput,
)
from jobtrail.schemas.common import EmptyInput
from jobtrail.usecase.context import AppContext

OFFER_OUTCOMES = (Outcome.OFFER_ACCEPTED, Outcome.OFFER_DECLINED)


def _offer_reached_at(row: ApplicationRow) -> datetime | None:
    """オファー面談の Stage が追加された時点を内定とみなす。無ければ内定系の終了時点。"""
    for stage in row.stages:
        if stage.type is StageType.OFFER:
            return stage.created_at
    return row.updated_at if row.outcome in OFFER_OUTCOMES else None


def _rate(numerator: int, denominator: int) -> float | None:
    return round(numerator / denominator, 3) if denominator else None


def _stage_rates(rows: list[ApplicationRow]) -> list[StagePassRate]:
    rates = []
    for stage_type in StageType:
        stages = [s for row in rows for s in row.stages if s.type is stage_type]
        decided = [s for s in stages if s.result is not StageResult.PENDING]
        passed = [s for s in decided if s.result is StageResult.PASSED]
        rates.append(
            StagePassRate(
                stage_type=stage_type,
                entered=len(stages),
                decided=len(decided),
                passed=len(passed),
                pass_rate=_rate(len(passed), len(decided)),
            )
        )
    return rates


def _days_to_offer(rows: list[ApplicationRow]) -> DaysToOffer:
    days = []
    for row in rows:
        offer_at = _offer_reached_at(row)
        if offer_at is not None and row.applied_at is not None:
            days.append((offer_at - row.applied_at).total_seconds() / 86400)
    return DaysToOffer(
        count=len(days),
        average=round(mean(days), 1) if days else None,
        median=round(median(days), 1) if days else None,
    )


def _channels(rows: list[ApplicationRow]) -> list[ChannelStats]:
    stats = []
    for channel in ApplicationChannel:
        members = [row for row in rows if row.channel is channel]
        offers = sum(1 for row in members if _offer_reached_at(row) is not None)
        rejected = sum(1 for row in members if row.outcome is Outcome.REJECTED)
        stats.append(
            ChannelStats(
                channel=channel,
                applied=len(members),
                offers=offers,
                rejected=rejected,
                offer_rate=_rate(offers, len(members)),
            )
        )
    return stats


def get_stats(ctx: AppContext, data: EmptyInput) -> StatsOutput:
    """ステージ別通過率、応募から内定までの日数、経路別比較を返す。"""
    with ctx.uow_factory() as uow:
        rows = [r for r in uow.application_reads.rows() if r.applied_at is not None]
    return StatsOutput(
        applied_total=len(rows),
        stage_pass_rates=_stage_rates(rows),
        days_to_offer=_days_to_offer(rows),
        channels=_channels(rows),
    )
