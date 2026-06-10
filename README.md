# SentinelXDR

SentinelXDR is a local-first XDR/SOC platform demo with FastAPI backend, MongoDB, Redis, Linux agent MVP, safe attack simulation lab, and a Lovable-generated React frontend integrated with real backend APIs.

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
