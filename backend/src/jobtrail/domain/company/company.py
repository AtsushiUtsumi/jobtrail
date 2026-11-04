from dataclasses import dataclass
from datetime import datetime
from typing import Any

from jobtrail.domain.shared.errors import DomainError
from jobtrail.domain.shared.ids import CompanyId, new_id
from jobtrail.domain.shared.value_objects import normalize_company_name, normalize_url


@dataclass(eq=False)
class Company:
    id: CompanyId
    name: str
    normalized_name: str
    url: str | None
    normalized_url: str | None
    priority: int | None
    memo: str
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None = None
    version: int = 0

    @classmethod
    def register(
        cls, name: str, url: str | None, priority: int | None, memo: str, now: datetime
    ) -> "Company":
        return cls(
            id=new_id(),
            name=name,
            normalized_name=normalize_company_name(name),
            url=url,
            normalized_url=normalize_url(url) if url else None,
            priority=priority,
            memo=memo,
            created_at=now,
            updated_at=now,
        )

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None

    def update(self, now: datetime, **changes: Any) -> None:
        self._ensure_active()
        if "name" in changes:
            self.name = changes["name"]
            self.normalized_name = normalize_company_name(self.name)
        if "url" in changes:
            self.url = changes["url"]
            self.normalized_url = normalize_url(self.url) if self.url else None
        if "priority" in changes:
            self.priority = changes["priority"]
        if "memo" in changes:
            self.memo = changes["memo"]
        self.updated_at = now

    def delete(self, now: datetime) -> None:
        self._ensure_active()
        self.deleted_at = now
        self.updated_at = now

    def restore(self, now: datetime) -> None:
        if not self.is_deleted:
            raise DomainError(
                "COMPANY_NOT_DELETED",
                f"企業は削除されていません: {self.name}",
                "restore_company は削除済みの企業にのみ使えます。",
            )
        self.deleted_at = None
        self.updated_at = now

    def _ensure_active(self) -> None:
        if self.is_deleted:
            raise DomainError(
                "COMPANY_DELETED",
                f"企業は削除済みです: {self.name}",
                "restore_company で復元してから操作してください。",
            )
