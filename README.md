# SentinelXDR

SentinelXDR is a local-first XDR/SOC platform demo with FastAPI backend, MongoDB, Redis, Linux agent MVP, safe attack simulation lab, and a Lovable-generated React frontend integrated with real backend APIs.

## Docker Compose Startup

Start the full local stack:

```bash
docker compose up --build
```

Then open:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8010`
- Swagger: `http://localhost:8010/docs`

Seed demo data:

```bash
python3 scripts/demo_seed.py --api-base-url http://localhost:8010
```

Stop:

```bash
docker compose down
```

Reset all Docker data:

```bash
docker compose down -v
```

Docker uses host ports `8010` for the backend, `8080` for the frontend, `27018` for MongoDB, and `6380` for Redis. Stop older local containers or manual services that use ports `8000`, `27017`, `6379`, or `8080` before starting the stack. If `8080` is busy, run the frontend on another host port:

```bash
FRONTEND_PORT=5174 docker compose up --build
```

## One-Command Local Dev

Requirements:

- Docker with Docker Compose.
- Python backend virtualenv at `backend/.venv`.
- Frontend package manager detected from lockfile. Current frontend uses Bun via `frontend/bun.lock`.

Start everything:

```bash
make dev
```

Or:

```bash
./scripts/start_dev.sh
```

If another local project already uses the default ports, override them:

```bash
BACKEND_PORT=8010 FRONTEND_PORT=5174 MONGO_PORT=27018 REDIS_PORT=6380 make dev
```

Stop everything:

```bash
make stop
```

Check health:

```bash
make check
```

URLs:

- Frontend: `http://localhost:5173`
- Backend: `http://localhost:8000`
- Swagger: `http://localhost:8000/docs`

## Manual Dev/Demo Startup

For a lightweight manual startup that runs the backend/frontend on the host and starts MongoDB/Redis with Docker Compose:

```bash
chmod +x scripts/run_sentinelxdr.sh scripts/stop_sentinelxdr.sh
./scripts/run_sentinelxdr.sh
./scripts/stop_sentinelxdr.sh
```

Manual URLs:

- Frontend: `http://localhost:8080`
- Backend: `http://localhost:8010`
- Swagger: `http://localhost:8010/docs`

Manual dependency ports:

- MongoDB: `mongodb://localhost:27018`
- Redis: `redis://localhost:6380/0`

The manual script waits for `http://localhost:8010/health/live`, `/health/db`, and `/health/redis` before starting the frontend. If MongoDB or Redis health checks fail, inspect `.dev/logs/backend.log` and `.dev/logs/compose.log`.

## Demo Flow

```bash
make dev
make demo-seed
make demo-smoke
```

Log in to the frontend with the credentials printed by `demo_seed.py`.

## Notes

- Demo data is tagged with `sentinelxdr-demo`.
- Lab scripts are simulation-only and must be used only on owned local lab systems.
- The local JWT secret is a placeholder. Change `JWT_SECRET_KEY` for any non-demo deployment.
