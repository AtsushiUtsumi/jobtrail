#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! docker info >/dev/null 2>&1; then
  echo "[jobtrail] ERROR: Docker is not running. Start Docker and try again." >&2
  exit 1
fi

if [ ! -f .env ]; then
  cp .env.example .env
  echo "[jobtrail] Created .env from .env.example"
fi

docker compose -p jobtrail down --remove-orphans
docker compose -p jobtrail up -d --build --wait

port="$(sed -n 's/^HTTP_PORT=\([0-9]*\).*/\1/p' .env | tail -n 1)"
base="http://localhost"
if [ -n "$port" ] && [ "$port" != "80" ]; then
  base="http://localhost:$port"
fi

echo
echo "[jobtrail] UI : $base"
echo "[jobtrail] MCP: $base/mcp"
