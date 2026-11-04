"""ドメイン例外。code（機械可読）・message（原因）・hint（次の一手）を持つ。"""

from enum import StrEnum
from typing import Any
from uuid import UUID


class ErrorKind(StrEnum):
    """アダプタが転送先のステータスへ写像するための分類。"""

    NOT_FOUND = "not_found"
    CONFLICT = "conflict"
    INVALID = "invalid"
    TOO_LARGE = "too_large"


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        hint: str = "",
        kind: ErrorKind = ErrorKind.CONFLICT,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.hint = hint
        self.kind = kind
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "hint": self.hint,
            "details": self.details,
        }


class NotFoundError(DomainError):
    def __init__(self, resource: str, resource_id: object, hint: str = "") -> None:
        super().__init__(
            "NOT_FOUND",
            f"{resource} が見つかりません: {resource_id}",
            hint or "検索系ツール（find_* / list_*）で ID を確認してください。",
            ErrorKind.NOT_FOUND,
            {"resource": resource, "id": str(resource_id)},
        )


class ConflictError(DomainError):
    def __init__(self, current_version: int | None = None) -> None:
        super().__init__(
            "CONFLICT",
            "他の更新と競合しました。",
            "最新の内容を再取得し、現在の version を expected_version に指定してください。",
            ErrorKind.CONFLICT,
            {"current_version": current_version},
        )


class DuplicateCompanyError(DomainError):
    def __init__(self, existing_id: UUID | None, name: str) -> None:
        super().__init__(
            "DUPLICATE_COMPANY",
            f"同じ企業が既に登録されています: {name}",
            "既存の企業の company_id を使ってください。",
            ErrorKind.CONFLICT,
            {"existing_id": str(existing_id) if existing_id else None},
        )


class ContentTooLargeError(DomainError):
    def __init__(self, actual: int, limit: int) -> None:
        super().__init__(
            "CONTENT_TOO_LARGE",
            f"本文が上限を超えています（{actual} 文字 / 上限 {limit} 文字）。",
            "本文を分割し、URL にページ番号などを付けて複数回に分けて保存してください。",
            ErrorKind.TOO_LARGE,
            {"actual": actual, "limit": limit},
        )


def check_version(current: int, expected: int | None) -> None:
    """expected が指定されたときのみ楽観ロックを検証する。"""
    if expected is not None and current != expected:
        raise ConflictError(current)
