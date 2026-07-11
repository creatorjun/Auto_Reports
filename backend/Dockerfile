# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libreoffice-nogui \
    fonts-noto-cjk \
    curl \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/reports /app/storage

RUN echo '#!/bin/sh' > /entrypoint.sh \
    && echo 'set -e' >> /entrypoint.sh \
    && echo 'echo "[entrypoint] DB migration..."' >> /entrypoint.sh \
    && echo 'alembic upgrade head' >> /entrypoint.sh \
    && echo 'echo "[entrypoint] DB migration done"' >> /entrypoint.sh \
    && echo 'exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 3600 --timeout-graceful-shutdown 3600 --h11-max-incomplete-event-size 0' >> /entrypoint.sh \
    && chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
