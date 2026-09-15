# syntax=docker/dockerfile:1.7

FROM ghcr.io/astral-sh/uv:0.11.28 AS uv

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PATH="/app/.venv/bin:$PATH" \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY backend/pyproject.toml backend/uv.lock backend/README.md ./
RUN uv sync --frozen --no-dev --no-install-project

COPY backend/src ./src
COPY backend/alembic.ini ./
COPY backend/migrations ./migrations
RUN uv sync --frozen --no-dev
RUN uv run playwright install --with-deps chromium \
    && rm -rf /var/lib/apt/lists/*

EXPOSE 8000

CMD ["uvicorn", "insightx.main:app", "--host", "0.0.0.0", "--port", "8000"]
