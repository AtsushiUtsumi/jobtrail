"""DNS rebinding 対策。認証を持たないため Host と Origin を localhost に限定する。"""

import json
from urllib.parse import urlsplit

from starlette.types import ASGIApp, Receive, Scope, Send

ALLOWED_HOSTNAMES = frozenset({"localhost", "127.0.0.1"})


def _hostname(netloc: str) -> str | None:
    try:
        return urlsplit(f"//{netloc}").hostname
    except ValueError:
        return None


def _origin_allowed(origin: str) -> bool:
    try:
        return urlsplit(origin).hostname in ALLOWED_HOSTNAMES
    except ValueError:
        return False


class LocalhostGuardMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self._app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        headers = {
            key.decode("latin-1").lower(): value.decode("latin-1")
            for key, value in scope["headers"]
        }
        if _hostname(headers.get("host", "")) not in ALLOWED_HOSTNAMES:
            await self._reject(send, "Host ヘッダーが許可されていません。")
            return
        origin = headers.get("origin")
        if scope["path"].startswith("/mcp") and origin and not _origin_allowed(origin):
            await self._reject(send, "Origin ヘッダーが許可されていません。")
            return
        await self._app(scope, receive, send)

    @staticmethod
    async def _reject(send: Send, message: str) -> None:
        body = json.dumps(
            {
                "code": "FORBIDDEN_HOST",
                "message": message,
                "hint": "http://localhost からアクセスしてください。",
                "details": {},
            },
            ensure_ascii=False,
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json")],
            }
        )
        await send({"type": "http.response.body", "body": body})
