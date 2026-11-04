from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from mcp.server.streamable_http_manager import (
    StreamableHTTPASGIApp,
    StreamableHTTPSessionManager,
)
from starlette.routing import Route

from jobtrail.adapters.mcp.server import build_server
from jobtrail.adapters.rest.error_handlers import register_error_handlers
from jobtrail.adapters.rest.router import build_router
from jobtrail.adapters.security import LocalhostGuardMiddleware
from jobtrail.bootstrap import build_context
from jobtrail.usecase.context import AppContext


def create_app(context: AppContext) -> FastAPI:
    session_manager = StreamableHTTPSessionManager(
        app=build_server(context), stateless=True, json_response=True
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        async with session_manager.run():
            yield

    app = FastAPI(
        title="jobtrail",
        version="0.1.0",
        lifespan=lifespan,
        openapi_url="/api/openapi.json",
        docs_url="/api/docs",
        redoc_url=None,
    )
    app.add_middleware(LocalhostGuardMiddleware)
    register_error_handlers(app)
    app.include_router(build_router(context))
    app.router.routes.append(Route("/mcp", endpoint=StreamableHTTPASGIApp(session_manager)))
    return app


app = create_app(build_context())
