@echo off
setlocal
cd /d "%~dp0"

docker info >nul 2>&1
if errorlevel 1 (
  echo [jobtrail] ERROR: Docker is not running. Start Docker and try again. 1>&2
  exit /b 1
)

if not exist .env (
  copy /y .env.example .env >nul
  echo [jobtrail] Created .env from .env.example
)

docker compose -p jobtrail down --remove-orphans
if errorlevel 1 exit /b 1

docker compose -p jobtrail up -d --build --wait
if errorlevel 1 (
  echo [jobtrail] ERROR: Failed to start. Check "docker compose -p jobtrail logs". 1>&2
  echo [jobtrail] If the port is in use, change HTTP_PORT in .env. 1>&2
  exit /b 1
)

set "HTTP_PORT=80"
for /f "usebackq tokens=1,* delims==" %%A in (".env") do (
  if /i "%%A"=="HTTP_PORT" set "HTTP_PORT=%%B"
)

set "BASE_URL=http://localhost"
if not "%HTTP_PORT%"=="80" set "BASE_URL=http://localhost:%HTTP_PORT%"

echo.
echo [jobtrail] UI : %BASE_URL%
echo [jobtrail] MCP: %BASE_URL%/mcp
endlocal
