"""REST と MCP が同じ形で返すエラー本文。"""

from collections.abc import Sequence
from typing import Any

from jobtrail.schemas.common import ErrorOutput


def validation_error_body(errors: Sequence[Any]) -> dict[str, Any]:
    fields = [
        {
            "field": ".".join(str(part) for part in error.get("loc", ())),
            "message": error.get("msg", ""),
        }
        for error in errors
    ]
    return ErrorOutput(
        code="VALIDATION_ERROR",
        message="入力が不正です。",
        hint="details.errors の項目を修正して再試行してください。",
        details={"errors": fields},
    ).model_dump()


def internal_error_body() -> dict[str, Any]:
    return ErrorOutput(
        code="INTERNAL_ERROR",
        message="内部エラーが発生しました。",
        hint="時間をおいて再試行し、続く場合はサーバーログを確認してください。",
    ).model_dump()
