"""registry からルートを生成する。ここに業務ロジックを書かない。"""

import inspect
import re
from collections.abc import Callable
from typing import Annotated, Any

from fastapi import APIRouter, Body, Path, Query
from pydantic import BaseModel, ConfigDict, create_model
from pydantic.fields import FieldInfo

from jobtrail.schemas.common import ErrorOutput
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.registry import USE_CASES, UseCase

BODY_PARAMETER = "body"


def _parameter(
    name: str, annotation: Any, marker: Any, field: FieldInfo | None
) -> inspect.Parameter:
    default = inspect.Parameter.empty
    if field is not None and not field.is_required():
        default = field.get_default(call_default_factory=True)
    return inspect.Parameter(
        name,
        inspect.Parameter.KEYWORD_ONLY,
        annotation=Annotated[annotation, marker],
        default=default,
    )


def _is_expected_version(name: str) -> bool:
    return name == "expected_version"


def _body_model(use_case: UseCase, path_fields: set[str]) -> type[BaseModel] | None:
    """パスに現れない項目から本文のモデルを作る。UI では expected_version を必須にする。"""
    fields: dict[str, Any] = {}
    for name, field in use_case.input_model.model_fields.items():
        if name in path_fields:
            continue
        fields[name] = (int, ...) if _is_expected_version(name) else (field.annotation, field)
    if not fields:
        return None
    if not path_fields and "expected_version" not in fields:
        return use_case.input_model
    return create_model(
        f"{use_case.input_model.__name__}Body",
        __config__=ConfigDict(extra="forbid"),
        **fields,
    )


def _build_endpoint(use_case: UseCase, context: AppContext) -> Callable[..., BaseModel]:
    model_fields = use_case.input_model.model_fields
    path_fields = re.findall(r"{(\w+)}", use_case.path)
    parameters = [
        _parameter(name, model_fields[name].annotation, Path(), None) for name in path_fields
    ]
    body_model: type[BaseModel] | None = None
    if use_case.method in ("GET", "DELETE"):
        for name, field in model_fields.items():
            if name in path_fields:
                continue
            if _is_expected_version(name):
                parameters.append(_parameter(name, int, Query(), None))
            else:
                parameters.append(_parameter(name, field.annotation, Query(), field))
    else:
        body_model = _body_model(use_case, set(path_fields))
        if body_model is not None:
            parameters.append(_parameter(BODY_PARAMETER, body_model, Body(), None))

    def endpoint(**kwargs: Any) -> BaseModel:
        body = kwargs.pop(BODY_PARAMETER, None)
        arguments = dict(kwargs)
        if isinstance(body, BaseModel):
            arguments |= body.model_dump(exclude_unset=True)
        return use_case.execute(context, arguments)

    endpoint.__name__ = use_case.name
    endpoint.__doc__ = use_case.description
    endpoint.__signature__ = inspect.Signature(  # type: ignore[attr-defined]
        sorted(parameters, key=lambda p: p.default is not inspect.Parameter.empty),
        return_annotation=use_case.output_model,
    )
    return endpoint


def build_router(context: AppContext) -> APIRouter:
    router = APIRouter(prefix="/api")
    for use_case in USE_CASES:
        router.add_api_route(
            use_case.path,
            _build_endpoint(use_case, context),
            methods=[use_case.method],
            status_code=use_case.status_code,
            response_model=use_case.output_model,
            operation_id=use_case.name,
            summary=use_case.description.splitlines()[0],
            responses={"default": {"model": ErrorOutput}},
        )
    return router
