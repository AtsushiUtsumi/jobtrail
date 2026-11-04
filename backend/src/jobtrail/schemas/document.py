from uuid import UUID

from pydantic import BaseModel, Field

from jobtrail.domain.document.document import DocumentKind
from jobtrail.schemas.common import InputModel, OutputModel, PageInput, Timestamp


class CreateDocumentInput(InputModel):
    name: str = Field(min_length=1)
    kind: DocumentKind
    body: str = Field(default="", description="指定すると第 1 版として保存する（Markdown）")
    note: str = ""


class AddDocumentVersionInput(InputModel):
    document_id: UUID
    body: str = Field(min_length=1, description="Markdown 本文")
    note: str = ""


class GetDocumentInput(InputModel):
    document_id: UUID


class ListDocumentsInput(PageInput):
    kind: DocumentKind | None = None


class AttachDocumentInput(InputModel):
    application_id: UUID
    document_version_id: UUID
    expected_version: int | None = None


class DocumentVersionOutput(OutputModel):
    id: UUID
    document_id: UUID
    number: int
    body: str
    created_at: Timestamp
    note: str
    submitted: bool = Field(default=False, description="応募に紐づいた版か（編集不可の印）")


class DocumentOutput(BaseModel):
    id: UUID
    name: str
    kind: DocumentKind
    created_at: Timestamp
    versions: list[DocumentVersionOutput]


class DocumentSummary(OutputModel):
    id: UUID
    name: str
    kind: DocumentKind
    created_at: Timestamp
    latest_version_number: int
