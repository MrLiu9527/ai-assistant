# syntax=docker/dockerfile:1

FROM node:22-bookworm-slim AS frontend

RUN corepack enable

ARG VITE_API_BASE_URL=/
ARG VITE_CHAT_ENTRY=/child/chat/
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
ENV VITE_CHAT_ENTRY=${VITE_CHAT_ENTRY}

WORKDIR /app/frontend

COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
COPY frontend/packages/shell/package.json ./packages/shell/
COPY frontend/packages/chat-app/package.json ./packages/chat-app/

RUN pnpm install --frozen-lockfile

COPY frontend/ ./
RUN pnpm run build


FROM python:3.12-slim-bookworm AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx bash curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md alembic.ini ./
COPY configs ./configs
COPY src ./src
COPY migrations ./migrations
COPY scripts ./scripts

RUN pip install --no-cache-dir .

RUN mkdir -p /usr/share/nginx/html/child/chat

COPY --from=frontend /app/frontend/packages/shell/dist/ /usr/share/nginx/html/
COPY --from=frontend /app/frontend/packages/chat-app/dist/ /usr/share/nginx/html/child/chat/

COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/entrypoint.sh"]
