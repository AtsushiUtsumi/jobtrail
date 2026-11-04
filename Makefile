COMPOSE = docker compose -p jobtrail
TEST_COMPOSE = docker compose -p jobtrail-test -f docker-compose.test.yml

.PHONY: up down test lint migrate backup openapi

up:
	./run.sh

down:
	$(COMPOSE) down --remove-orphans

test:
	$(TEST_COMPOSE) run --rm --build test; status=$$?; $(TEST_COMPOSE) down -v; exit $$status

lint:
	cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run lint-imports
	cd frontend && npm run lint && npm run typecheck && npm test

migrate:
	$(COMPOSE) exec app alembic upgrade head

backup:
	mkdir -p backups
	$(COMPOSE) exec -T db sh -c 'pg_dump -U "$$POSTGRES_USER" -d "$$POSTGRES_DB" --clean --if-exists' > backups/jobtrail-$$(date +%Y%m%d-%H%M%S).sql

openapi:
	cd backend && uv run python -m jobtrail.adapters.rest.export_openapi > ../frontend/src/api/openapi.json
	cd frontend && npm run gen:api
