#!/bin/sh
set -eu

host="${POSTGRES_HOST:-postgres}"
port="${POSTGRES_PORT:-5432}"
echo "Waiting for PostgreSQL at ${host}:${port}..."

python - <<PY
import os, socket, time

host = os.environ.get("POSTGRES_HOST", "postgres")
port = int(os.environ.get("POSTGRES_PORT", "5432"))
for i in range(60):
    try:
        s = socket.create_connection((host, port), timeout=2)
        s.close()
        print("PostgreSQL is up.")
        break
    except OSError:
        if i == 59:
            raise SystemExit("Timeout waiting for PostgreSQL.")
        time.sleep(1)
PY

echo "Running database init (idempotent)..."
python scripts/init_db.py --no-drop

exec "$@"
