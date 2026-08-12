# Makefile
.PHONY: up down build logs migrate ps restart trigger

up:
	docker compose up -d

build:
	docker compose build --no-cache

down:
	docker compose down

logs:
	docker compose logs -f

restart:
	docker compose restart backend

migrate:
	docker compose exec backend alembic upgrade head

ps:
	docker compose ps

trigger:
	curl -s -X POST http://localhost/api/v1/trigger/ | python3 -m json.tool
