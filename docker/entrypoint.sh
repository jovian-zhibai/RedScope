#!/bin/bash
set -e

echo "[RedScope] Running database migrations..."
cd /app
alembic upgrade head 2>/dev/null || echo "[RedScope] Alembic migration skipped (init_db will create tables)"

echo "[RedScope] Starting application..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000
