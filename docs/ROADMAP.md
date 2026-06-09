# SentinelXDR — Product Roadmap

**Version:** 0.1.0 (Phase 0)
**Status:** Draft
**Last Updated:** 2026-06-09

---

## Overview

This roadmap describes the phased delivery plan for SentinelXDR from initial architecture through production-ready deployment. Each phase builds on the previous, with a fully functional demo environment as the anchor milestone for Phase 0/1.

---

## Phase 0 — Foundation & Architecture (Current)

**Goal:** Establish project foundation, documentation, and architecture. No production code yet.

### Deliverables

- [x] Product Specification (`PRODUCT_SPEC.md`)
- [x] System Architecture (`ARCHITECTURE.md`)
- [x] API Contracts (`API_CONTRACTS.md`)
- [x] Database Schema (`DATABASE_SCHEMA.md`)
- [x] Security Model (`SECURITY_MODEL.md`)
- [x] Lab Demo Plan (`LAB_DEMO_PLAN.md`)
- [x] Roadmap (`ROADMAP.md`)
- [ ] Docker Compose skeleton (all services declared, no app code)
- [ ] Git repository structure and branch strategy
- [ ] CI pipeline scaffolding (GitHub Actions / GitLab CI)
- [ ] Development environment setup guide (`README.md`)

### Exit Criteria

- All documentation files reviewed and approved
- Repository structure established with empty service directories
- `docker compose up` starts all infrastructure services (Mongo, Redis, Nginx)
- No application logic yet — infrastructure skeleton only

---

## Phase 1 — Core Pipeline (Agent → Ingest → Detect → Alert)

**Goal:** End-to-end telemetry pipeline operational. Detect first attacks in lab.

### Milestone 1.1 — Agent MVP (Linux)

- Linux agent skeleton (Python)
  - Process creation events (via `/proc` polling or auditd)
  - Network connection events
  - File access events (inotify)
- Agent → Backend secure transport (HTTPS + JWT)
- Agent self-registration and heartbeat

### Milestone 1.2 — Agent MVP (Windows)

- Windows agent skeleton (Python)
  - Process events via WMI event subscriptions
  - Network events via ETW consumer
  - Registry modification events
- Same transport layer as Linux agent

### Milestone 1.3 — Ingestion API

- `POST /api/v1/ingest` endpoint
- Event schema validation (Pydantic models)
- Event normalization to Common Event Format
- Normalized events written to MongoDB `events` collection
- Events pushed to Redis `stream:events:raw`

### Milestone 1.4 — Detection Engine v1 (Rule-Based)

- Detection worker consuming from Redis stream
- YAML rule loader and evaluator
- First 10 detection rules (see Lab Demo Plan)
- Alert creation in MongoDB `alerts` collection
- Real-time alert push via WebSocket

### Milestone 1.5 — Basic Dashboard

- Alert list view with severity badges
- Alert detail view (raw event data, MITRE mapping)
- Asset inventory page
- Agent health monitor

### Phase 1 Exit Criteria

- Linux and Windows agents collect and deliver events
- At least 10 lab attack scenarios detected end-to-end
- Alert visible in dashboard within 5 seconds of attack execution
- All alerts tagged with correct MITRE ATT&CK technique

---

## Phase 2 — Intelligence & Investigation

**Goal:** Add ML-based detection, deep investigation tooling, and correlation engine.

### Milestone 2.1 — Anomaly Detection Models

- Behavioral baseline construction per asset (7-day rolling window)
- Isolation Forest model for outlier detection
- Autoencoder for sequence anomaly detection
- Model training pipeline (offline batch)
- Model serving integrated with detection worker

### Milestone 2.2 — Correlation Engine

- Multi-event pattern matching (time-windowed)
- Attack chain assembly (kill chain stages)
- Cross-domain correlation (endpoint + network + identity)
- Incident creation from correlated alert clusters

### Milestone 2.3 — Investigation Workbench

- Attack timeline view (chronological event sequence)
- Process tree renderer (parent/child process hierarchy)
- Network connection graph (D3.js force-directed)
- Entity pivot: host → user → alerts → network connections
- Evidence download (raw events for a given alert)

### Milestone 2.4 — Asset Intelligence

- Automated asset discovery from agent registrations
- Asset risk scoring (based on alerts and exposure)
- User entity tracking and behavioral profiling
- Network topology visualization

### Milestone 2.5 — Threat Intelligence Integration

- IOC database (IPs, domains, file hashes)
- Auto-enrichment of alerts with IOC matches
- Threat intelligence feed ingestion (STIX/TAXII compatible)

### Phase 2 Exit Criteria

- ML model detects at least 3 behavioral anomaly scenarios
- Correlation engine assembles multi-stage attack chains
- Investigation workbench renders full attack timeline and process tree
- Asset risk scores updated in real time

---

## Phase 3 — Response & Reporting

**Goal:** Automated response playbooks, executive reporting, and operational hardening.

### Milestone 3.1 — Automated Response Playbooks

- Playbook definition format (YAML)
- Built-in playbooks: host isolation, IP block, account disable
- Playbook trigger conditions (severity threshold, rule match)
- Response execution via agent command channel
- Response result tracking and rollback capability

### Milestone 3.2 — Case Management

- Alert → Case assignment workflow
- Case status tracking (New → In Progress → Resolved → Closed)
- Analyst notes and evidence attachment
- SLA timer tracking (MTTD, MTTR)
- Case export (PDF report)

### Milestone 3.3 — Reporting Engine

- MITRE ATT&CK coverage heatmap (auto-generated)
- Detection summary by domain and severity
- Weekly / monthly executive report templates
- Alert trend charts (volume, severity distribution, top rules)
- Scheduled report delivery (email)

### Milestone 3.4 — Platform Hardening

- Role-based access control (Admin, Analyst, Read-Only)
- MFA support for platform login
- API rate limiting and abuse detection
- Full audit log review UI
- Secrets management via environment isolation

### Phase 3 Exit Criteria

- Automated isolation playbook successfully executed in lab
- Executive report generated covering all lab scenarios
- MITRE ATT&CK heatmap reflects all detected techniques
- RBAC enforced with three distinct user roles

---

## Phase 4 — Scale & Integrations

**Goal:** Production-grade deployment, third-party integrations, and multi-tenancy.

### Milestone 4.1 — Cloud-Native Deployment

- Kubernetes manifests (Helm charts)
- Horizontal Pod Autoscaler for ingestion and detection workers
- Persistent Volume Claims for MongoDB and Redis
- Ingress controller with TLS termination

### Milestone 4.2 — SOAR Integrations

- Jira / ServiceNow ticketing integration
- Slack / Teams alert notifications
- PagerDuty incident escalation
- Webhook output for generic integrations

### Milestone 4.3 — Extended Collectors

- AWS CloudTrail integration
- Azure Active Directory sign-in logs
- Office 365 audit log integration
- Zeek / Suricata network sensor integration

### Milestone 4.4 — Multi-Tenancy

- Tenant isolation at data layer
- Per-tenant detection rule sets
- Tenant-scoped user management
- MSSP billing and usage reporting

### Phase 4 Exit Criteria

- Platform deployed on Kubernetes with auto-scaling
- At least 3 SOAR integrations operational
- Multi-tenant demo with 2 isolated tenants

---

## Dependency Map

```
Phase 0 (Docs + Infra)
    └── Phase 1 (Core Pipeline)
            ├── Phase 2 (Intelligence)
            │       └── Phase 3 (Response)
            │               └── Phase 4 (Scale)
            └── Phase 3 (Response) [partial, runs in parallel with Phase 2]
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Agent instability on diverse OS versions | Medium | High | Extensive VM-based testing matrix |
| False positive rate too high in ML models | High | Medium | Conservative thresholds; human-in-loop tuning |
| MongoDB performance at scale | Low | High | Index strategy review; sharding plan prepared |
| Lab isolation breach (attack escapes VM) | Low | Critical | Air-gapped network; snapshot-based VM reset |
| Detection worker lag under load | Medium | High | Redis stream consumer group scaling + backpressure |

---

*This roadmap is subject to revision as development progresses. All phases beyond Phase 1 are tentative.*
