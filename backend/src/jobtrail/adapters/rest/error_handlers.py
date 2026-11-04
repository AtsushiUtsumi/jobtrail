from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from jobtrail.adapters.errors import validation_error_body
from jobtrail.domain.shared.errors import DomainError, ErrorKind

STATUS_BY_KIND = {
    ErrorKind.NOT_FOUND: 404,
    ErrorKind.CONFLICT: 409,
    ErrorKind.INVALID: 422,
    ErrorKind.TOO_LARGE: 413,
}


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def handle_domain_error(_: Request, error: DomainError) -> JSONResponse:
        return JSONResponse(status_code=STATUS_BY_KIND[error.kind], content=error.to_dict())

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(_: Request, error: RequestValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=validation_error_body(error.errors()))

    @app.exception_handler(ValidationError)
    async def handle_validation(_: Request, error: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content=validation_error_body(error.errors()))
