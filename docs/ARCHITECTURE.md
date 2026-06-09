# SentinelXDR — System Architecture

**Version:** 0.1.0 (Phase 0)
**Status:** Draft
**Last Updated:** 2026-06-09

---

## 1. Architecture Overview

SentinelXDR follows an **event-driven, microservice-oriented architecture** with a clearly separated ingestion layer, processing layer, storage layer, and presentation layer. All components are containerized and orchestrated via Docker Compose.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         SENTINELXDR PLATFORM                        │
│                                                                     │
│  ┌───────────────┐   ┌───────────────┐   ┌───────────────────────┐  │
│  │   COLLECTORS  │   │  INGESTION    │   │   DETECTION ENGINE    │  │
│  │               │   │  PIPELINE     │   │                       │  │
│  │ • Win Agent   │──▶│               │──▶│ • Rule Engine         │  │
│  │ • Lin Agent   │   │ • FastAPI      │   │ • ML Anomaly Models   │  │
│  │ • Syslog      │   │   Receiver    │   │ • Correlation Engine  │  │
│  │ • Cloud API   │   │ • Normalizer  │   │ • ATT&CK Mapper       │  │
│  └───────────────┘   │ • Redis Queue │   └──────────┬────────────┘  │
│                      └───────────────┘              │               │
│                                                     ▼               │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                        STORAGE LAYER                          │  │
│  │                                                               │  │
│  │   ┌─────────────┐   ┌─────────────┐   ┌─────────────────┐   │  │
│  │   │   MongoDB   │   │    Redis    │   │  File / Object  │   │  │
│  │   │             │   │             │   │    Storage      │   │  │
│  │   │ • Events    │   │ • Event Q   │   │ • PCAP dumps    │   │  │
│  │   │ • Alerts    │   │ • Alert Q   │   │ • Log archives  │   │  │
│  │   │ • Assets    │   │ • Session   │   │ • ML models     │   │  │
│  │   │ • Rules     │   │   Cache     │   │                 │   │  │
│  │   └─────────────┘   └─────────────┘   └─────────────────┘   │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                     │               │
│  ┌──────────────────────────────────────────────────▼────────────┐  │
│  │                      API GATEWAY (FastAPI)                    │  │
│  │   /api/v1/events  /api/v1/alerts  /api/v1/assets  /api/v1/…  │  │
│  └──────────────────────────────────┬────────────────────────────┘  │
│                                     │                               │
│  ┌──────────────────────────────────▼────────────────────────────┐  │
│  │                    FRONTEND (React + Tailwind)                 │  │
│  │   Dashboard | Alert Queue | Investigation | Assets | Reports  │  │
│  └───────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. Component Breakdown

### 2.1 Collector Layer

**Purpose:** Gather raw telemetry from monitored systems and deliver it to the ingestion pipeline.

| Component | Language | Transport | Description |
|---|---|---|---|
| Windows Agent | Python | HTTPS/WebSocket | Collects process, file, registry, network events via WMI/ETW |
| Linux Agent | Python | HTTPS/WebSocket | Collects process, file, network events via auditd/eBPF |
| Syslog Receiver | Python | UDP/TCP 514 | Accepts syslog from firewalls, routers, switches |
| Cloud Collector | Python | REST API polling | Pulls events from AWS CloudTrail, Azure Activity Log |

Agent responsibilities:
- Local buffering during connectivity loss (up to configurable limit)
- Heartbeat reporting every 30 seconds
- Self-update capability via signed packages
- Configurable collection policies pushed from backend

### 2.2 Ingestion Pipeline

**Purpose:** Receive, validate, normalize, and queue raw events for processing.

```
Raw Event (JSON/CEF/Syslog)
    │
    ▼
┌─────────────────────────────────────┐
│        FastAPI Ingestion API        │
│  POST /api/v1/ingest                │
│  • Authentication (Agent JWT)       │
│  • Rate limiting per agent          │
│  • Schema validation                │
│  • Decompression (gzip/zstd)        │
└──────────────────┬──────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│          Event Normalizer           │
│  • Maps vendor schemas → Common     │
│    Event Format (CEF-based)         │
│  • Timestamp normalization (UTC)    │
│  • Asset enrichment (hostname →     │
│    asset record lookup)             │
│  • GeoIP enrichment for IPs         │
└──────────────────┬──────────────────┘
                   │
                   ▼
         Redis Event Queue
         (stream: events:raw)
```

### 2.3 Detection Engine

**Purpose:** Consume normalized events and produce alerts when attack patterns are identified.

```
Redis Event Queue
    │
    ▼
┌──────────────────────────────────────────┐
│           Detection Worker Pool          │
│  (horizontally scalable Python workers)  │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │         Rule Engine                 │ │
│  │  • YAML Sigma-compatible rules      │ │
│  │  • Condition matching (AND/OR/NOT)  │ │
│  │  • Time-window aggregation          │ │
│  │  • Threshold-based triggers         │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │       Anomaly Detection Model       │ │
│  │  • Per-entity behavioral baseline   │ │
│  │  • Statistical deviation scoring    │ │
│  │  • Isolation Forest / Autoencoder   │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │       Correlation Engine            │ │
│  │  • Multi-event pattern matching     │ │
│  │  • Attack chain assembly            │ │
│  │  • Cross-domain signal fusion       │ │
│  └─────────────────────────────────────┘ │
│                                          │
│  ┌─────────────────────────────────────┐ │
│  │       MITRE ATT&CK Mapper           │ │
│  │  • Tactic + Technique tagging       │ │
│  │  • Sub-technique enrichment         │ │
│  └─────────────────────────────────────┘ │
└──────────────────────────────────────────┘
    │
    ▼
Alert → MongoDB alerts collection
Alert → Redis alert notification stream
```

### 2.4 Storage Layer

**MongoDB Collections:**

| Collection | Purpose |
|---|---|
| `events` | Normalized telemetry events (TTL-indexed) |
| `alerts` | Detected alerts with full context |
| `incidents` | Grouped/correlated alert clusters |
| `assets` | Managed endpoints, users, network entities |
| `rules` | Detection rule definitions |
| `playbooks` | Automated response playbook definitions |
| `audit_log` | Immutable platform action log |
| `users` | Platform user accounts |
| `agents` | Registered agent metadata and health |
| `threat_intel` | IOC and threat intelligence records |

**Redis Usage:**

| Key Pattern | Purpose | TTL |
|---|---|---|
| `stream:events:raw` | Raw event ingestion queue | N/A (consumer groups) |
| `stream:alerts:new` | Alert notification stream | N/A |
| `cache:asset:{id}` | Asset record cache | 5 minutes |
| `cache:geoip:{ip}` | GeoIP lookup cache | 24 hours |
| `session:{token}` | User session data | 8 hours |
| `ratelimit:agent:{id}` | Per-agent rate limit counters | 1 minute sliding |

### 2.5 API Gateway

**Purpose:** Unified REST API surface for frontend and external integrations.

- Built with **FastAPI** (Python 3.12+)
- JWT-based authentication for user sessions
- Mutual TLS + signed JWT for agent authentication
- OpenAPI 3.0 spec auto-generated at `/api/v1/docs`
- WebSocket endpoint for real-time alert streaming to frontend
- Versioned API (`/api/v1/...`) for forward compatibility

### 2.6 Frontend

**Purpose:** Security operations dashboard and investigation workbench.

- **React 18** with TypeScript
- **Tailwind CSS** for styling
- **Recharts / D3.js** for telemetry visualizations
- **React Query** for API data fetching and caching
- **Zustand** for global state management
- **Socket.IO** client for real-time alert updates

Key views:
- Live Alert Queue
- Incident Investigation Workbench
- Asset Inventory
- Detection Rules Manager
- MITRE ATT&CK Coverage Heatmap
- System Health Dashboard

---

## 3. Data Flow

### 3.1 Normal Event Ingestion Flow

```
1. Agent collects OS event
2. Agent batches events (up to 100 or 1 second, whichever first)
3. Agent compresses batch (gzip) and POSTs to /api/v1/ingest
4. Ingestion API validates JWT, rate limits, decompresses
5. Normalizer maps to Common Event Format
6. Normalized event written to MongoDB events collection
7. Event pushed to Redis stream:events:raw
8. Detection worker consumes event from Redis stream
9. Rule engine + anomaly model evaluate event
10. If alert triggered: written to MongoDB alerts, pushed to stream:alerts:new
11. Frontend receives alert via WebSocket notification
12. SOC analyst investigates via dashboard
```

### 3.2 Alert Response Flow

```
1. Alert appears in SOC dashboard
2. Analyst opens alert → investigation workbench loads timeline
3. Analyst reviews process tree, network connections, user activity
4. Analyst triggers response action (isolate host / block IP / disable account)
5. Response command queued in Redis
6. Agent polls for pending commands or receives push via WebSocket
7. Agent executes response (network isolation, process kill, etc.)
8. Execution result reported back to platform
9. Audit log entry created
10. Alert status updated to In Progress / Resolved
```

---

## 4. Deployment Architecture (Docker Compose)

```yaml
# Service topology (logical)
services:
  mongo          # MongoDB 7.x - primary data store
  redis          # Redis 7.x - cache and message queue
  backend-api    # FastAPI application (gunicorn + uvicorn workers)
  detection-worker  # Detection engine workers (scaled replicas)
  frontend       # React app served via Nginx
  nginx          # Reverse proxy and TLS termination

networks:
  internal       # Backend services (not exposed externally)
  public         # Frontend + API only
```

All services communicate on the `internal` Docker network. Only `nginx` and `frontend` are exposed on the host network. MongoDB and Redis are never directly reachable from outside the Docker network.

---

## 5. Security Architecture Summary

See `SECURITY_MODEL.md` for full detail. Key principles:

- **Zero Trust between services**: All inter-service calls use service tokens
- **Encryption in transit**: TLS 1.3 for all HTTP, mTLS for agent communication
- **Encryption at rest**: MongoDB encrypted storage, secrets managed via environment variables (HashiCorp Vault in production)
- **Least privilege**: Each service container runs as non-root user with minimal capabilities
- **Immutable audit log**: All platform actions recorded; audit collection has no update/delete permissions

---

## 6. Scalability Design

| Bottleneck | Scaling Strategy |
|---|---|
| Event ingestion | Horizontal: multiple FastAPI instances behind load balancer |
| Detection processing | Horizontal: multiple detection worker replicas consuming from Redis streams |
| MongoDB | Vertical first; replica set + sharding for production scale |
| Redis | Sentinel for HA; Redis Cluster for extreme throughput |
| Frontend | Stateless; CDN distribution for production |

---

## 7. Technology Stack Summary

| Layer | Technology | Version Target |
|---|---|---|
| API Framework | FastAPI | 0.115.x |
| ASGI Server | Uvicorn + Gunicorn | Latest stable |
| Database | MongoDB | 7.x |
| Cache / Queue | Redis | 7.x |
| Frontend Framework | React | 18.x |
| Frontend Styling | Tailwind CSS | 3.x |
| Agent Runtime | Python | 3.12+ |
| Containerization | Docker | 25.x |
| Orchestration (dev) | Docker Compose | 2.x |
| Reverse Proxy | Nginx | 1.25.x |

---

*This document describes the Phase 0 target architecture for SentinelXDR.*
