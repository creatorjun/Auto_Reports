#!/bin/sh
set -e

echo "[entrypoint] DB 마이그레이션 실행 중..."
alembic upgrade head
echo "[entrypoint] DB 마이그레이션 완료 ✅"

exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 30
