.PHONY: dev stop check backend-test frontend-test demo-seed demo-smoke docker-up docker-up-detached docker-down docker-logs docker-reset docker-seed docker-smoke

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
