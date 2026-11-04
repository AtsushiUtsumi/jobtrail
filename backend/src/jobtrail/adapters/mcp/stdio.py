"""stdio エントリポイント。HTTP で接続できないクライアント向けの代替経路。"""

import anyio
from mcp.server.stdio import stdio_server

from jobtrail.adapters.mcp.server import build_server
from jobtrail.bootstrap import build_context


async def _main() -> None:
    server = build_server(build_context())
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    anyio.run(_main)
