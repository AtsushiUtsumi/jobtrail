from collections.abc import Sequence
from typing import Protocol

from jobtrail.domain.document.document import Document, DocumentKind, DocumentVersion
from jobtrail.domain.shared.ids import DocumentId, DocumentVersionId


class DocumentRepository(Protocol):
    def add(self, document: Document) -> None: ...

    def get(self, document_id: DocumentId) -> Document | None: ...

    def get_version(self, version_id: DocumentVersionId) -> DocumentVersion | None: ...

    def search(
        self, kind: DocumentKind | None, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]: ...

    def submitted_version_ids(self, document_id: DocumentId) -> set[DocumentVersionId]:
        """応募に紐づいた（提出済みの）版の ID を返す。"""
        ...
