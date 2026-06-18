# Security Hardening

## Production Config Guards

The backend validates critical settings when `ENVIRONMENT=production`:

- Rejects `DEBUG=true`.
- Rejects the built-in default `JWT_SECRET_KEY`.
- Rejects wildcard CORS origin `*`.

These guards are covered by `backend/tests/test_config.py`.

## Required Production Settings

Use a dedicated `.env.production`:

```env
ENVIRONMENT=production
DEBUG=false
JWT_SECRET_KEY=<openssl-rand-hex-32-output>
BACKEND_CORS_ORIGINS=https://your-xdr-domain.example
FRONTEND_PUBLIC_URL=https://your-xdr-domain.example
EXPOSE_API_DOCS=false
```

`BACKEND_CORS_ORIGINS` should be a comma-separated list of exact frontend origins. Do not use `*`.

## API Documentation

The production compose file sets `EXPOSE_API_DOCS=false`. This disables:

- `/docs`
- `/redoc`
- `/openapi.json`

The nginx config still proxies these paths so local and staging deployments can enable them with `EXPOSE_API_DOCS=true`.

## Network Exposure

In `docker-compose.prod.yml`, only nginx publishes a host port. Backend, MongoDB, Redis, and the frontend static container are reachable only on the Docker network.

## Secrets

Do not commit `.env.production`. Rotate `JWT_SECRET_KEY` if it is exposed. Existing access and refresh tokens signed by the old key become invalid after rotation.

## Audit Logs

SentinelAI XDR writes immutable audit records for security-significant actions:

- User registration, login, logout, and token refresh.
- Agent registration and disablement.
- Detection rule create, update, enable, and disable.
- Alert status updates.
- Incident status, assignment, and summary updates.
- Attack chain status updates.

Audit records are read-only through `GET /api/audit` and `GET /api/audit/{audit_id}`. There are no update or delete audit APIs.

Audit visibility is restricted to `ORG_ADMIN` and `SUPER_ADMIN`. `ANALYST` and `VIEWER` receive `403`, and cross-organization audit access returns `404`.

Metadata is recursively redacted for sensitive keys including passwords, tokens, API keys, JWTs, authorization headers, secrets, refresh tokens, and agent keys. Audit write failures are logged internally and do not break the primary API request flow.

## Remaining Production Controls

Before internet exposure, add TLS termination, host firewall rules, centralized logs, image vulnerability scanning, and MongoDB authentication or an external managed MongoDB deployment.
