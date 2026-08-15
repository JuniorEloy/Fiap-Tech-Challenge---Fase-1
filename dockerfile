# ------------------------------------------------------------------------------
# Stage 1 - Build
# ------------------------------------------------------------------------------

FROM python:3.14.6-slim-bookworm AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11.28 /uv /uvx /bin/

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

COPY app ./app

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ------------------------------------------------------------------------------
# Stage 2 - Runtime
# ------------------------------------------------------------------------------

FROM python:3.14.6-slim-bookworm

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

RUN addgroup --system app && \
    adduser --system --ingroup app app

COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/app /app/app

COPY --chown=app:app alembic ./alembic
COPY --chown=app:app alembic.ini .
COPY --chmod=755 --chown=app:app docker/entrypoint.sh .

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/')" || exit 1

CMD ["./entrypoint.sh"]