FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

FROM node:22-bookworm-slim AS node-runtime

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# FFmpeg handles Discord audio; libatomic is required by the Node.js binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg libatomic1 \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 appuser

COPY --from=builder /app/.venv /app/.venv
COPY --from=node-runtime /usr/local/bin/node /usr/local/bin/node

COPY --chown=appuser:appuser ytmusicbot/ ./ytmusicbot/
COPY --chown=appuser:appuser random_songs_config.json ./

RUN mkdir -p cache logs random_songs secrets \
    && chown -R appuser:appuser cache logs random_songs secrets

USER appuser

CMD ["python", "-m", "ytmusicbot.discord"]
