from uuid import UUID

from jobtrail.domain.document.document import Document
from jobtrail.domain.shared.errors import NotFoundError, check_version
from jobtrail.domain.shared.value_objects import ensure_text_size
from jobtrail.schemas.application import ApplicationOutput
from jobtrail.schemas.common import Page
from jobtrail.schemas.document import (
    AddDocumentVersionInput,
    AttachDocumentInput,
    CreateDocumentInput,
    DocumentOutput,
    DocumentSummary,
    DocumentVersionOutput,
    GetDocumentInput,
    ListDocumentsInput,
)
from jobtrail.usecase.application.commands import load_application
from jobtrail.usecase.application.presenters import to_output
from jobtrail.usecase.company.commands import load_company
from jobtrail.usecase.context import AppContext, UnitOfWork


def _load_document(uow: UnitOfWork, document_id: UUID) -> Document:
    document = uow.documents.get(document_id)
    if document is None:
        raise NotFoundError("書類", document_id, "list_documents で ID を確認してください。")
    return document


def _to_output(uow: UnitOfWork, document: Document) -> DocumentOutput:
    submitted = uow.documents.submitted_version_ids(document.id)
    versions = [
        DocumentVersionOutput.model_validate(v).model_copy(update={"submitted": v.id in submitted})
        for v in document.versions
    ]
    return DocumentOutput(
        id=document.id,
        name=document.name,
        kind=document.kind,
        created_at=document.created_at,
        versions=versions,
    )


def create_document(ctx: AppContext, data: CreateDocumentInput) -> DocumentOutput:
    """書類を作成する。body を渡すと第 1 版として保存する。"""
    ensure_text_size(data.body, ctx.settings.max_raw_text_chars)
    with ctx.uow_factory() as uow:
        now = ctx.now()
        document = Document.create(data.name, data.kind, now)
        if data.body:
            document.add_version(data.body, data.note, now)
        uow.documents.add(document)
        uow.commit()
        return _to_output(uow, document)


def add_document_version(ctx: AppContext, data: AddDocumentVersionInput) -> DocumentOutput:
    """書類に新しい版を追加する。既存の版は変更できない。"""
    ensure_text_size(data.body, ctx.settings.max_raw_text_chars)
    with ctx.uow_factory() as uow:
        document = _load_document(uow, data.document_id)
        document.add_version(data.body, data.note, ctx.now())
        uow.commit()
        return _to_output(uow, document)


def get_document(ctx: AppContext, data: GetDocumentInput) -> DocumentOutput:
    """書類を全ての版つきで取得する。"""
    with ctx.uow_factory() as uow:
        return _to_output(uow, _load_document(uow, data.document_id))


def list_documents(ctx: AppContext, data: ListDocumentsInput) -> Page[DocumentSummary]:
    """書類を本文なしで一覧する。"""
    with ctx.uow_factory() as uow:
        items, total = uow.documents.search(data.kind, data.limit, data.offset)
        return Page(
            items=[
                DocumentSummary(
                    id=d.id,
                    name=d.name,
                    kind=d.kind,
                    created_at=d.created_at,
                    latest_version_number=len(d.versions),
                )
                for d in items
            ],
            total=total,
            limit=data.limit,
            offset=data.offset,
        )


def attach_document_to_application(ctx: AppContext, data: AttachDocumentInput) -> ApplicationOutput:
    """提出した書類の版を応募に紐づける。紐づいた版は提出済みとして扱う。"""
    with ctx.uow_factory() as uow:
        application = load_application(uow, data.application_id)
        check_version(application.version, data.expected_version)
        if uow.documents.get_version(data.document_version_id) is None:
            raise NotFoundError(
                "書類の版", data.document_version_id, "get_document で版の ID を確認してください。"
            )
        application.attach_submitted_document(data.document_version_id, ctx.now())
        uow.commit()
        return to_output(application, load_company(uow, application.company_id).name)
