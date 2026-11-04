from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from jobtrail.domain.shared.ids import DocumentId, DocumentVersionId, new_id


class DocumentKind(StrEnum):
    CAREER_HISTORY = "career_history"
    RESUME = "resume"
    OTHER = "other"


@dataclass(eq=False)
class DocumentVersion:
    """本文を書き換える手段を持たない。修正は新しい版の追加で行う。"""

    id: DocumentVersionId
    document_id: DocumentId
    number: int
    body: str
    created_at: datetime
    note: str


@dataclass(eq=False)
class Document:
    id: DocumentId
    name: str
    kind: DocumentKind
    created_at: datetime
    versions: list[DocumentVersion] = field(default_factory=list)

    @classmethod
    def create(cls, name: str, kind: DocumentKind, now: datetime) -> "Document":
        return cls(id=new_id(), name=name, kind=kind, created_at=now)

    def add_version(self, body: str, note: str, now: datetime) -> DocumentVersion:
        version = DocumentVersion(
            id=new_id(),
            document_id=self.id,
            number=len(self.versions) + 1,
            body=body,
            created_at=now,
            note=note,
        )
        self.versions.append(version)
        return version
