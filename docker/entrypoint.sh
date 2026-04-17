#!/usr/bin/env bash
set -euo pipefail

export APP_ENV="${APP_ENV:-production}"
export DEBUG="${DEBUG:-false}"

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "ERROR: DATABASE_URL is required" >&2
  exit 1
fi

if [[ "${INIT_DB:-0}" == "1" ]]; then
  echo "Running database initialization (INIT_DB=1)..."
  python scripts/init_db.py
fi

WORKERS="${UVICORN_WORKERS:-2}"

uvicorn src.api.app:app \
  --host 127.0.0.1 \
  --port 8000 \
  --workers "${WORKERS}" \
  --log-level "${UVICORN_LOG_LEVEL:-info}" &
UVICORN_PID=$!

cleanup() {
  kill -TERM "${UVICORN_PID}" 2>/dev/null || true
  nginx -s quit 2>/dev/null || true
  wait "${UVICORN_PID}" 2>/dev/null || true
}

trap cleanup EXIT INT TERM

nginx -c /etc/nginx/nginx.conf -g "daemon off;" &
NGINX_PID=$!

wait "${NGINX_PID}"
