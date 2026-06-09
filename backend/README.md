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

Event endpoints:

- `POST /api/events/ingest`
- `GET /api/events`
- `GET /api/events/{event_id}`

Detection and alert endpoints:

- `GET /api/detections/rules`
- `GET /api/detections/rules/{rule_id}`
- `POST /api/detections/rules`
- `PATCH /api/detections/rules/{rule_id}`
- `POST /api/detections/rules/{rule_id}/disable`
- `POST /api/detections/rules/{rule_id}/enable`
- `GET /api/detections/results`
- `GET /api/detections/results/{result_id}`
- `GET /api/alerts`
- `GET /api/alerts/{alert_id}`
- `PATCH /api/alerts/{alert_id}/status`

Incident endpoints:

- `GET /api/incidents`
- `GET /api/incidents/{incident_id}`
- `PATCH /api/incidents/{incident_id}/status`
- `PATCH /api/incidents/{incident_id}/assign`
- `PATCH /api/incidents/{incident_id}/summary`

Attack chain endpoints:

- `GET /api/attack-chains`
- `GET /api/attack-chains/{chain_id}`
- `GET /api/incidents/{incident_id}/attack-chain`
- `PATCH /api/attack-chains/{chain_id}/status`

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

Event ingestion also uses `X-Agent-Key` only. The backend assigns
`organization_id`, `agent_id`, and `received_at` server-side, then evaluates
enabled built-in and organization rules. Matching alerts are grouped into
incidents by organization, agent, MITRE technique or title, and the
`INCIDENT_CORRELATION_WINDOW_MINUTES` setting:

```bash
curl -X POST http://localhost:8000/api/events/ingest \
  -H "X-Agent-Key: sxag_..." \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_type": "process_start",
        "severity": "info",
        "source": "linux",
        "title": "Process started",
        "description": "bash started",
        "raw_event": {"pid": 1234},
        "normalized_fields": {"process.name": "bash"},
        "tags": ["process"]
      }
    ]
  }'
```

Event reads use bearer auth and are organization-scoped:

```bash
curl "http://localhost:8000/api/events?severity=info&source=linux&limit=50" \
  -H "Authorization: Bearer <access_token>"
```

Detection rules use safe AND-based conditions only. Supported operators are
`equals`, `contains`, `regex`, `in`, `gt`, `gte`, `lt`, and `lte`.

```json
{
  "name": "Custom Curl Download",
  "description": "Curl download command observed",
  "enabled": true,
  "severity": "medium",
  "source": "linux",
  "event_type": "process_start",
  "conditions": {
    "all": [
      {
        "field": "normalized_fields.command_line",
        "operator": "contains",
        "value": "curl"
      }
    ]
  },
  "mitre_tactics": ["Command and Control"],
  "mitre_techniques": ["T1105"],
  "tags": ["custom"]
}
```

Incidents are organization-scoped and dashboard-friendly. `GET /api/incidents`
supports `status`, `severity`, `agent_id`, `mitre_technique`, `limit`, and
`skip`. Analysts and admins can update status, assignment, and summary; viewers
can list and read only.

Attack chains are generated automatically from incidents and linked alerts,
detections, and events. They include deterministic risk and confidence scores,
kill-chain phases, a timeline, a graph for visualization, a readable threat
story, and recommended actions. `GET /api/attack-chains` supports `status`,
`severity`, `agent_id`, `mitre_technique`, `min_risk_score`, `limit`, and `skip`.

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
