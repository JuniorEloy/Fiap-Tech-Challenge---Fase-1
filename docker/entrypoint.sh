#!/bin/sh

set -e

echo "Aplicando migrations..."

alembic upgrade head

echo "Executando seed..."

python -m app.scripts.seed

echo "Iniciando FastAPI..."

exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8000