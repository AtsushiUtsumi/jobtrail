from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.orm import Session

from jobtrail.domain.document.document import Document, DocumentKind, DocumentVersion
from jobtrail.domain.shared.ids import DocumentId, DocumentVersionId
from jobtrail.infra.db.models import applications, document_versions, documents, submissions


class SqlDocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, document: Document) -> None:
        self._session.add(document)

    def get(self, document_id: DocumentId) -> Document | None:
        return self._session.get(Document, document_id)

    def get_version(self, version_id: DocumentVersionId) -> DocumentVersion | None:
        return self._session.get(DocumentVersion, version_id)

    def search(
        self, kind: DocumentKind | None, limit: int, offset: int
    ) -> tuple[Sequence[Document], int]:
        conditions = [documents.c.kind == kind] if kind is not None else []
        total = self._session.scalar(
            sa.select(sa.func.count()).select_from(documents).where(*conditions)
        )
        items = self._session.scalars(
            sa.select(Document)
            .where(*conditions)
            .order_by(documents.c.created_at.desc())
            .limit(limit)
            .offset(offset)
        ).all()
        return items, total or 0

    def submitted_version_ids(self, document_id: DocumentId) -> set[DocumentVersionId]:
        versions = sa.select(document_versions.c.id).where(
            document_versions.c.document_id == document_id
        )
        attached = sa.select(applications.c.submitted_document_version_id).where(
            applications.c.submitted_document_version_id.in_(versions)
        )
        recorded = sa.select(submissions.c.document_version_id).where(
            submissions.c.document_version_id.in_(versions)
        )
        return set(self._session.scalars(attached.union(recorded)).all())
