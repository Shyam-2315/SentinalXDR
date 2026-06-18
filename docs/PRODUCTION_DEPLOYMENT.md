# SentinelAI XDR Production Deployment

This phase adds a production Docker stack without changing the existing local development compose file or startup scripts.

## Files

- `docker-compose.prod.yml`: production stack for nginx, backend, frontend, MongoDB, and Redis.
- `deploy/nginx/nginx.conf`: public reverse proxy.
- `backend/Dockerfile.prod`: non-root Python 3.12 FastAPI image.
- `frontend/Dockerfile.prod`: Vite build stage and nginx static serve stage.
- `.env.production.example`: production environment template.

## First-Time Setup

Create a production env file from the example:

```bash
cp .env.production.example .env.production
```

Edit `.env.production` before deployment:

```env
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=<generate-a-long-random-secret>
MONGODB_URI=mongodb://mongo:27017/sentinelxdr
REDIS_URL=redis://redis:6379/0
BACKEND_CORS_ORIGINS=https://your-xdr-domain.example
FRONTEND_PUBLIC_URL=https://your-xdr-domain.example
EXPOSE_API_DOCS=false
NGINX_HTTP_PORT=80
```

Generate a JWT secret with:

```bash
openssl rand -hex 32
```

## Startup

Exact production startup command:

```bash
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
```

Equivalent Make target:

```bash
make prod-up
```

## Operations

```bash
make prod-build
make prod-up
make prod-logs
make prod-smoke
make prod-down
```

To remove containers and volumes:

```bash
make prod-reset
```

`prod-reset` deletes MongoDB and Redis Docker volumes. Back up data first.

## Routing

The public nginx container exposes one HTTP port and proxies internally:

- `/` -> frontend static nginx container
- `/api` -> backend
- `/api/v1` -> backend
- `/health` -> backend
- `/docs`, `/redoc`, `/openapi.json` -> backend

Production defaults set `EXPOSE_API_DOCS=false`, so documentation routes return `404`. For local or staging production-stack testing, set `EXPOSE_API_DOCS=true`.

## Audit and Compliance

The production backend stores audit logs in MongoDB in the `audit_logs` collection. Audit logs capture actor, organization, action, resource, status, IP address, user agent, timestamp, description, and redacted metadata.

Audit APIs:

- `GET /api/audit`
- `GET /api/audit/{audit_id}`

Only `ORG_ADMIN` and `SUPER_ADMIN` can read audit logs. Audit logs are organization-scoped and immutable through the API.

## Verification

Run:

```bash
docker compose -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.prod.yml up --build -d
curl -i http://localhost/
curl -i http://localhost/health/live
curl -i http://localhost/health/ready
python3 scripts/prod_smoke_check.py --base-url http://localhost --openapi disabled
```

For a non-local domain, replace `http://localhost` with `FRONTEND_PUBLIC_URL`.

## Notes

- Backend runs `uvicorn app.main:app --host 0.0.0.0 --port 8010 --workers 2`.
- Backend healthcheck calls `GET /health/live`.
- Redis runs with appendonly persistence enabled.
- MongoDB and Redis are not published to the host in the production compose file.
