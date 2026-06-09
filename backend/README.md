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
