FROM python:3.12-slim AS base
ENV UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never PYTHONUNBUFFERED=1
RUN pip install --no-cache-dir uv==0.13.7
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src
RUN uv sync --frozen --no-dev
ENV PATH=/app/.venv/bin:$PATH

FROM base AS test
RUN uv sync --frozen
COPY tests ./tests

FROM base AS production
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn jobtrail.main:app --host 0.0.0.0 --port 8000"]
