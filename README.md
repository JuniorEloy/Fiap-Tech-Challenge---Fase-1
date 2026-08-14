# rodar somente bd:
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d postgres

# rodar o fastapi:
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# rodar migração bd
uv run alembic revision --autogenerate -m "mensagem"
uv run alembic upgrade head

# rodar a seed
uv run python seed.py

# testes
docker compose -f docker-compose.test.yml up -d

APP_ENV=test alembic upgrade head
APP_ENV=test uv run python app/scripts/seed.py

APP_ENV=test uv run pytest --cov=app --cov-report=term-missing     
APP_ENV=test uv run pytest
APP_ENV=test uv run pytest --junitxml=report.xml