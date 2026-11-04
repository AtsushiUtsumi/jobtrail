"""registry から MCP ツールを生成する。ここに業務ロジックを書かない。"""

import json
import logging
from typing import Any

import anyio.to_thread
from mcp.server.context import ServerRequestContext
from mcp.server.lowlevel import Server
from mcp_types import (
    CallToolRequestParams,
    CallToolResult,
    ListToolsResult,
    PaginatedRequestParams,
    TextContent,
    Tool,
    ToolAnnotations,
)
from pydantic import ValidationError

from jobtrail.adapters.errors import internal_error_body, validation_error_body
from jobtrail.adapters.mcp.descriptions import SERVER_INSTRUCTIONS, describe
from jobtrail.domain.shared.errors import DomainError, NotFoundError
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.registry import USE_CASES, UseCase

logger = logging.getLogger(__name__)


def _to_tool(use_case: UseCase) -> Tool:
    return Tool(
        name=use_case.name,
        description=describe(use_case),
        input_schema=use_case.input_model.model_json_schema(),
        annotations=ToolAnnotations(
            read_only_hint=use_case.read_only,
            destructive_hint=use_case.destructive,
        ),
    )


def _json_result(payload: dict[str, Any], *, is_error: bool = False) -> CallToolResult:
    text = json.dumps(payload, ensure_ascii=False)
    return CallToolResult(content=[TextContent(type="text", text=text)], is_error=is_error)


def call_use_case(
    context: AppContext, use_cases: dict[str, UseCase], name: str, arguments: dict[str, Any]
) -> CallToolResult:
    use_case = use_cases.get(name)
    if use_case is None:
        return _json_result(NotFoundError("ツール", name).to_dict(), is_error=True)
    try:
        output = use_case.execute(context, arguments)
    except DomainError as error:
        return _json_result(error.to_dict(), is_error=True)
    except ValidationError as error:
        return _json_result(validation_error_body(error.errors()), is_error=True)
    except Exception:
        logger.exception("ツール %s の実行に失敗しました", name)
        return _json_result(internal_error_body(), is_error=True)
    return _json_result(output.model_dump(mode="json"))


def build_server(context: AppContext) -> Server[Any]:
    use_cases = {use_case.name: use_case for use_case in USE_CASES}
    tools = [_to_tool(use_case) for use_case in USE_CASES]

    async def list_tools(
        _: ServerRequestContext[Any], params: PaginatedRequestParams | None
    ) -> ListToolsResult:
        return ListToolsResult(tools=tools)

    async def call_tool(
        _: ServerRequestContext[Any], params: CallToolRequestParams
    ) -> CallToolResult:
        return await anyio.to_thread.run_sync(
            call_use_case, context, use_cases, params.name, params.arguments or {}
        )

    return Server(
        "jobtrail",
        version="0.1.0",
        instructions=SERVER_INSTRUCTIONS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )
