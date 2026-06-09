# SentinelXDR — API Contracts

**Version:** 0.3.0 (Phase 3)
**Status:** Draft
**Last Updated:** 2026-06-09
**Base URL:** `https://{host}`
**Format:** REST/JSON, OpenAPI 3.0 compatible

---

## 1. Authentication

### 1.1 User Authentication

All user-facing endpoints require a Bearer JWT in the `Authorization` header.

```
Authorization: Bearer <access_token>
```

Tokens are obtained via the login endpoint. Access and refresh token expiries are configured with `ACCESS_TOKEN_EXPIRE_MINUTES` and `REFRESH_TOKEN_EXPIRE_DAYS`.

### 1.2 Agent Authentication

Agents authenticate heartbeat calls using a pre-issued **Agent API Key**. The plaintext key is returned only once during agent registration, and only its hash is stored.

```
X-Agent-Key: <agent_api_key>
```

### 1.3 Error Responses (All Endpoints)

All errors follow a consistent structure:

```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired token",
    "request_id": "req_abc123"
  }
}
```

Standard HTTP status codes apply: `400`, `401`, `403`, `404`, `409`, `422`, `429`, `500`.

---

## 2. Authentication Endpoints

### Roles

Supported roles:

- `SUPER_ADMIN`
- `ORG_ADMIN`
- `ANALYST`
- `VIEWER`

Supported user statuses:

- `active`
- `disabled`

---

### POST /api/auth/register

Register a user. The first registered user creates an organization and becomes `ORG_ADMIN`. Later registrations must include an existing `organization_id`.

**Request:**
```json
{
  "email": "analyst@example.com",
  "password": "s3cur3P@ss",
  "display_name": "Alice Smith",
  "organization_name": "Acme Security"
}
```

**Response `201`:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "usr_01HXYZ",
    "organization_id": "org_01HXYZ",
    "email": "analyst@example.com",
    "display_name": "Alice Smith",
    "role": "ORG_ADMIN",
    "status": "active"
  },
  "organization": {
    "id": "org_01HXYZ",
    "name": "Acme Security"
  }
}
```

**Response `409`:** Email is already registered.

---

### POST /api/auth/login

Authenticate a user and obtain access + refresh tokens.

**Request:**
```json
{
  "email": "analyst@example.com",
  "password": "s3cur3P@ss"
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGci...",
  "refresh_token": "eyJhbGci...",
  "token_type": "bearer",
  "user": {
    "id": "usr_01HXYZ",
    "organization_id": "org_01HXYZ",
    "email": "analyst@example.com",
    "display_name": "Alice Smith",
    "role": "ORG_ADMIN",
    "status": "active"
  },
  "organization": {
    "id": "org_01HXYZ",
    "name": "Acme Security"
  }
}
```

**Response `401`:**
```json
{
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Email or password is incorrect"
  }
}
```

---

### GET /api/auth/me

Return the current authenticated user and organization.

**Headers:** `Authorization: Bearer <access_token>`

**Response `200`:**
```json
{
  "user": {
    "id": "usr_01HXYZ",
    "organization_id": "org_01HXYZ",
    "email": "analyst@example.com",
    "display_name": "Alice Smith",
    "role": "ORG_ADMIN",
    "status": "active"
  },
  "organization": {
    "id": "org_01HXYZ",
    "name": "Acme Security"
  }
}
```

---

### POST /api/auth/refresh

Exchange a refresh token for a new access token.

**Request:**
```json
{
  "refresh_token": "eyJhbGci..."
}
```

**Response `200`:**
```json
{
  "access_token": "eyJhbGci...",
  "token_type": "bearer"
}
```

---

### POST /api/auth/logout

Revoke the current session.

**Headers:** `Authorization: Bearer <token>`

**Response `200`:**
```json
{
  "status": "ok"
}
```

---

## 3. Ingestion Endpoints (Agent → Platform)

### POST /ingest

Submit a batch of telemetry events from an agent.

**Headers:**
- `X-Agent-ID: <agent_uuid>`
- `X-Agent-Token: <signed_jwt>`
- `Content-Encoding: gzip` (optional, recommended)
- `Content-Type: application/json`

**Request:**
```json
{
  "agent_id": "agt_01HXYZ",
  "hostname": "WORKSTATION-01",
  "os": "linux",
  "agent_version": "1.0.0",
  "batch_id": "batch_uuid_v4",
  "timestamp": "2026-06-09T12:00:00Z",
  "events": [
    {
      "event_id": "evt_uuid_v4",
      "event_type": "process_create",
      "timestamp": "2026-06-09T11:59:58Z",
      "data": {
        "pid": 4521,
        "ppid": 1234,
        "process_name": "bash",
        "command_line": "bash -c 'whoami'",
        "user": "root",
        "executable_path": "/bin/bash",
        "md5": "abc123def456",
        "sha256": "abcdef1234567890..."
      }
    },
    {
      "event_id": "evt_uuid_v4_2",
      "event_type": "network_connection",
      "timestamp": "2026-06-09T11:59:59Z",
      "data": {
        "pid": 4521,
        "protocol": "TCP",
        "src_ip": "192.168.1.10",
        "src_port": 54321,
        "dst_ip": "203.0.113.45",
        "dst_port": 4444,
        "direction": "outbound",
        "bytes_sent": 1024,
        "bytes_recv": 512
      }
    }
  ]
}
```

**Response `202`:**
```json
{
  "batch_id": "batch_uuid_v4",
  "accepted": 2,
  "rejected": 0,
  "message": "Batch accepted for processing"
}
```

**Response `207` (partial success):**
```json
{
  "batch_id": "batch_uuid_v4",
  "accepted": 1,
  "rejected": 1,
  "rejections": [
    {
      "event_id": "evt_uuid_v4_2",
      "reason": "SCHEMA_VALIDATION_FAILED",
      "detail": "Field 'dst_ip' failed IP format validation"
    }
  ]
}
```

---

## 4. Agent Endpoints

### POST /api/agents/register

Register a new agent for the authenticated user's organization.

**Headers:** `Authorization: Bearer <access_token>`

Allowed roles: `SUPER_ADMIN`, `ORG_ADMIN`, `ANALYST`.

**Request:**
```json
{
  "name": "workstation-01",
  "hostname": "WORKSTATION-01",
  "os_type": "linux",
  "agent_version": "1.0.0",
  "ip_address": "10.0.0.5",
  "tags": ["endpoint", "lab"]
}
```

**Response `201`:**
```json
{
  "agent": {
    "id": "agt_01HXYZ",
    "organization_id": "org_01HXYZ",
    "name": "workstation-01",
    "hostname": "WORKSTATION-01",
    "os_type": "linux",
    "agent_version": "1.0.0",
    "status": "offline",
    "last_seen_at": null,
    "ip_address": "10.0.0.5",
    "tags": ["endpoint", "lab"],
    "created_at": "2026-06-09T12:00:00Z",
    "updated_at": "2026-06-09T12:00:00Z"
  },
  "api_key": "sxag_..."
}
```

---

### POST /api/agents/heartbeat

Report agent liveness. This endpoint does not use JWT auth.

**Headers:** `X-Agent-Key: <agent_api_key>`

**Request:**
```json
{
  "agent_version": "1.0.1",
  "ip_address": "10.0.0.5"
}
```

**Response `200`:**
```json
{
  "status": "ok"
}
```

---

### GET /api/agents

List agents in the authenticated user's organization. Disabled agents are included with `status: "disabled"`.

**Headers:** `Authorization: Bearer <access_token>`

Allowed roles: `SUPER_ADMIN`, `ORG_ADMIN`, `ANALYST`, `VIEWER`.

**Response `200`:**
```json
{
  "agents": [
    {
      "id": "agt_01HXYZ",
      "organization_id": "org_01HXYZ",
      "name": "workstation-01",
      "hostname": "WORKSTATION-01",
      "os_type": "linux",
      "agent_version": "1.0.1",
      "status": "online",
      "last_seen_at": "2026-06-09T12:05:00Z",
      "ip_address": "10.0.0.5",
      "tags": ["endpoint", "lab"],
      "created_at": "2026-06-09T12:00:00Z",
      "updated_at": "2026-06-09T12:05:00Z"
    }
  ]
}
```

---

### GET /api/agents/{agent_id}

Get one agent in the authenticated user's organization. Cross-organization access returns `404`.

**Headers:** `Authorization: Bearer <access_token>`

Allowed roles: `SUPER_ADMIN`, `ORG_ADMIN`, `ANALYST`, `VIEWER`.

---

### POST /api/agents/{agent_id}/disable

Disable one agent in the authenticated user's organization. Disabled agents cannot heartbeat successfully.

**Headers:** `Authorization: Bearer <access_token>`

Allowed roles: `SUPER_ADMIN`, `ORG_ADMIN`.

**Response `200`:**
```json
{
  "agent": {
    "id": "agt_01HXYZ",
    "organization_id": "org_01HXYZ",
    "name": "workstation-01",
    "hostname": "WORKSTATION-01",
    "os_type": "linux",
    "agent_version": "1.0.1",
    "status": "disabled",
    "last_seen_at": "2026-06-09T12:05:00Z",
    "ip_address": "10.0.0.5",
    "tags": ["endpoint", "lab"],
    "created_at": "2026-06-09T12:00:00Z",
    "updated_at": "2026-06-09T12:06:00Z"
  }
}
```

---

## 5. Alert Endpoints

### GET /alerts

List alerts with filtering and pagination.

**Headers:** `Authorization: Bearer <token>`

**Query Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `severity` | string | Filter: `critical`, `high`, `medium`, `low`, `info` |
| `status` | string | Filter: `new`, `in_progress`, `resolved`, `closed` |
| `domain` | string | Filter: `endpoint`, `network`, `identity`, `web`, `cloud`, `data` |
| `asset_id` | string | Filter by related asset |
| `from` | ISO8601 | Start of time range |
| `to` | ISO8601 | End of time range |
| `page` | integer | Page number (default: 1) |
| `limit` | integer | Items per page (default: 25, max: 100) |
| `sort` | string | `created_at:desc` (default), `severity:desc` |

**Response `200`:**
```json
{
  "data": [
    {
      "id": "alr_01HXYZ",
      "title": "Reverse Shell Detected",
      "description": "Process 'bash' established outbound TCP connection to suspicious IP on port 4444",
      "severity": "critical",
      "status": "new",
      "domain": "endpoint",
      "rule_id": "rule_reverse_shell_001",
      "mitre": {
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
        "technique": "Non-Standard Port",
        "technique_id": "T1571"
      },
      "asset": {
        "id": "ast_01HABC",
        "hostname": "WORKSTATION-01",
        "ip": "192.168.1.10"
      },
      "event_count": 3,
      "first_seen": "2026-06-09T11:59:58Z",
      "last_seen": "2026-06-09T12:00:01Z",
      "created_at": "2026-06-09T12:00:02Z",
      "assigned_to": null
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 25,
    "total": 1,
    "pages": 1
  }
}
```

---

### GET /alerts/{alert_id}

Retrieve full alert detail including all related events.

**Response `200`:**
```json
{
  "id": "alr_01HXYZ",
  "title": "Reverse Shell Detected",
  "description": "...",
  "severity": "critical",
  "status": "new",
  "domain": "endpoint",
  "rule_id": "rule_reverse_shell_001",
  "rule_name": "Reverse Shell via Bash",
  "mitre": {
    "tactic": "Command and Control",
    "tactic_id": "TA0011",
    "technique": "Non-Standard Port",
    "technique_id": "T1571"
  },
  "asset": {
    "id": "ast_01HABC",
    "hostname": "WORKSTATION-01",
    "ip": "192.168.1.10",
    "os": "linux",
    "risk_score": 87
  },
  "events": [
    {
      "event_id": "evt_uuid_v4",
      "event_type": "process_create",
      "timestamp": "2026-06-09T11:59:58Z",
      "data": { "..." : "..." }
    }
  ],
  "timeline": [
    {
      "timestamp": "2026-06-09T11:59:58Z",
      "description": "bash spawned by sshd (PID 1234)",
      "event_type": "process_create"
    },
    {
      "timestamp": "2026-06-09T12:00:00Z",
      "description": "Outbound TCP to 203.0.113.45:4444",
      "event_type": "network_connection"
    }
  ],
  "notes": [],
  "first_seen": "2026-06-09T11:59:58Z",
  "last_seen": "2026-06-09T12:00:01Z",
  "created_at": "2026-06-09T12:00:02Z",
  "assigned_to": null
}
```

---

### PATCH /alerts/{alert_id}

Update alert status or assignment.

**Request:**
```json
{
  "status": "in_progress",
  "assigned_to": "usr_01HXYZ",
  "note": "Investigating — confirmed malicious C2 connection"
}
```

**Response `200`:** Updated alert object.

---

## 6. Asset Endpoints

### GET /assets

List all registered assets.

**Query Parameters:** `page`, `limit`, `os`, `status` (`online`, `offline`, `isolated`), `risk_min` (integer)

**Response `200`:**
```json
{
  "data": [
    {
      "id": "ast_01HABC",
      "hostname": "WORKSTATION-01",
      "ip": "192.168.1.10",
      "os": "linux",
      "os_version": "Ubuntu 22.04.3 LTS",
      "status": "online",
      "risk_score": 87,
      "last_seen": "2026-06-09T12:00:00Z",
      "agent_id": "agt_01HXYZ",
      "alert_counts": {
        "critical": 1,
        "high": 0,
        "medium": 2
      }
    }
  ],
  "pagination": { "page": 1, "limit": 25, "total": 1, "pages": 1 }
}
```

---

### GET /assets/{asset_id}

Full asset detail with alert history and agent info.

### POST /assets/{asset_id}/isolate

Trigger network isolation of an endpoint.

**Request:**
```json
{
  "reason": "Active C2 connection detected",
  "alert_id": "alr_01HXYZ"
}
```

**Response `202`:**
```json
{
  "command_id": "cmd_01HXYZ",
  "status": "queued",
  "message": "Isolation command queued for agent"
}
```

### POST /assets/{asset_id}/unisolate

Remove network isolation from an endpoint.

---

## 7. Rules Endpoints

### GET /rules

List all detection rules.

**Query Parameters:** `domain`, `enabled` (bool), `severity`, `mitre_technique`

**Response `200`:**
```json
{
  "data": [
    {
      "id": "rule_reverse_shell_001",
      "name": "Reverse Shell via Bash",
      "description": "Detects bash process establishing outbound connection to high-numbered port",
      "domain": "endpoint",
      "severity": "critical",
      "enabled": true,
      "mitre_technique": "T1059.004",
      "created_at": "2026-06-09T10:00:00Z",
      "updated_at": "2026-06-09T10:00:00Z"
    }
  ]
}
```

### POST /rules

Create a new detection rule. Request body: full rule definition object.

### PUT /rules/{rule_id}

Replace a rule definition.

### PATCH /rules/{rule_id}

Partially update a rule (e.g., enable/disable).

### DELETE /rules/{rule_id}

Delete a detection rule.

---

## 8. WebSocket — Real-Time Alert Stream

### WS /ws/alerts

Establishes a real-time connection for alert notifications.

**Connection:** `wss://{host}/api/v1/ws/alerts?token=<access_token>`

**Server → Client message (new alert):**
```json
{
  "type": "alert:new",
  "payload": {
    "id": "alr_01HXYZ",
    "title": "Reverse Shell Detected",
    "severity": "critical",
    "asset_hostname": "WORKSTATION-01",
    "created_at": "2026-06-09T12:00:02Z"
  }
}
```

**Server → Client message (alert updated):**
```json
{
  "type": "alert:updated",
  "payload": {
    "id": "alr_01HXYZ",
    "status": "in_progress",
    "assigned_to": "usr_01HXYZ"
  }
}
```

**Client → Server message (subscribe to specific asset):**
```json
{
  "type": "subscribe",
  "filter": {
    "asset_id": "ast_01HABC"
  }
}
```

---

## 9. System / Health Endpoints

### GET /health/live

Platform liveness check. No authentication required.

**Response `200`:**
```json
{
  "status": "ok",
  "service": "SentinelXDR API",
  "version": "0.1.0"
}
```

### GET /health/ready

Readiness check including MongoDB and Redis dependency status. No authentication required.

**Response `200`:**
```json
{
  "status": "ready",
  "dependencies": {
    "mongodb": { "name": "mongodb", "status": "healthy", "latency_ms": 2 },
    "redis": { "name": "redis", "status": "healthy", "latency_ms": 1 }
  }
}
```

### GET /health/db

MongoDB dependency health. Returns `503` when unavailable.

### GET /health/redis

Redis dependency health. Returns `503` when unavailable.

---

## 10. Common Event Types Reference

| `event_type` | Description | Key Fields |
|---|---|---|
| `process_create` | New process spawned | `pid`, `ppid`, `process_name`, `command_line`, `user`, `executable_path` |
| `process_terminate` | Process exited | `pid`, `process_name`, `exit_code`, `duration_ms` |
| `network_connection` | TCP/UDP connection established | `pid`, `protocol`, `src_ip`, `src_port`, `dst_ip`, `dst_port`, `direction` |
| `network_dns` | DNS query | `pid`, `query`, `query_type`, `response_ips`, `response_code` |
| `file_create` | File created | `pid`, `path`, `size`, `md5`, `sha256` |
| `file_modify` | File modified | `pid`, `path`, `old_size`, `new_size` |
| `file_delete` | File deleted | `pid`, `path` |
| `user_login` | User authentication event | `user`, `auth_type`, `src_ip`, `success`, `failure_reason` |
| `user_privilege_escalation` | Privilege change detected | `user`, `method`, `target_privilege` |
| `registry_modify` | Windows registry key modified | `pid`, `key_path`, `value_name`, `old_value`, `new_value` |

---

*This contract is the authoritative API specification for SentinelXDR Phase 0/1. All endpoints subject to change before production release.*
