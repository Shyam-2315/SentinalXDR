# SentinelXDR Backend

FastAPI backend foundation with async MongoDB, Redis, authentication, RBAC, and
organization-aware multi-tenancy.

## Requirements

- Python 3.12+
- Docker and Docker Compose

## Local Development

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.

Health endpoints:

- `GET /health/live`
- `GET /health/ready`
- `GET /health/db`
- `GET /health/redis`

Auth endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `POST /api/auth/refresh`
- `POST /api/auth/logout`

Agent endpoints:

- `POST /api/agents/register`
- `POST /api/agents/heartbeat`
- `GET /api/agents`
- `GET /api/agents/{agent_id}`
- `POST /api/agents/{agent_id}/disable`

Register and login return a frontend-friendly payload:

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer",
  "user": {
    "id": "usr_...",
    "organization_id": "org_...",
    "email": "analyst@example.com",
    "display_name": "Alice Analyst",
    "role": "ORG_ADMIN",
    "status": "active"
  },
  "organization": {
    "id": "org_...",
    "name": "Acme Security"
  }
}
```

The first registered user creates an organization and becomes `ORG_ADMIN`.
Additional users must register with an existing `organization_id`.

Agent registration requires a bearer token for `SUPER_ADMIN`, `ORG_ADMIN`, or
`ANALYST`. It returns the plaintext `api_key` only once:

```json
{
  "agent": {
    "id": "agt_...",
    "organization_id": "org_...",
    "name": "workstation-1",
    "hostname": "workstation-1.local",
    "os_type": "linux",
    "agent_version": "1.0.0",
    "status": "offline",
    "last_seen_at": null,
    "ip_address": null,
    "tags": ["endpoint"],
    "created_at": "2026-06-09T00:00:00Z",
    "updated_at": "2026-06-09T00:00:00Z"
  },
  "api_key": "sxag_..."
}
```

Agent heartbeat uses `X-Agent-Key` only:

```bash
curl -X POST http://localhost:8000/api/agents/heartbeat \
  -H "X-Agent-Key: sxag_..." \
  -H "Content-Type: application/json" \
  -d '{"agent_version":"1.0.1","ip_address":"10.0.0.5"}'
```

OpenAPI docs are available at `http://localhost:8000/api/v1/docs`.

## Docker Compose

```bash
cd backend
cp .env.example .env
docker compose up --build
```

The Compose stack starts:

- `backend`: FastAPI app on `http://localhost:8000`
- `mongo`: MongoDB 7
- `redis`: Redis 7

## Tests and Linting

```bash
cd backend
python -m pytest -q
ruff check .
```
