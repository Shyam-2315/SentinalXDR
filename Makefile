.PHONY: dev stop check backend-test frontend-test demo-seed demo-smoke docker-up docker-up-detached docker-down docker-logs docker-reset docker-seed docker-smoke prod-up prod-down prod-logs prod-build prod-reset prod-smoke

PROD_COMPOSE = docker compose --env-file .env.production -f docker-compose.prod.yml

dev:
	./scripts/start_dev.sh

stop:
	./scripts/stop_dev.sh

check:
	./scripts/check_dev.sh

backend-test:
	cd backend && . .venv/bin/activate && python -m pytest -q && ruff check .

frontend-test:
	cd frontend && if command -v bun >/dev/null 2>&1; then bun run build; else npm run build; fi

demo-seed:
	python3 scripts/demo_seed.py

demo-smoke:
	python3 scripts/demo_smoke_check.py

docker-up:
	docker compose up --build

docker-up-detached:
	docker compose up --build -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-reset:
	docker compose down -v

docker-seed:
	python3 scripts/demo_seed.py --api-base-url http://localhost:8010

docker-smoke:
	python3 scripts/demo_smoke_check.py --api-base-url http://localhost:8010

prod-up:
	$(PROD_COMPOSE) up --build -d

prod-down:
	$(PROD_COMPOSE) down

prod-logs:
	$(PROD_COMPOSE) logs -f

prod-build:
	$(PROD_COMPOSE) build

prod-reset:
	$(PROD_COMPOSE) down -v

prod-smoke:
	python3 scripts/prod_smoke_check.py --base-url $${FRONTEND_PUBLIC_URL:-http://localhost}
