# SentinelXDR — Security Model

**Version:** 0.1.0 (Phase 0)
**Status:** Draft
**Last Updated:** 2026-06-09

---

## 1. Security Philosophy

SentinelXDR is a security operations platform and is therefore held to a higher security standard than typical applications. A compromise of the platform would undermine the security posture of every monitored environment. The security model is built on the following principles:

1. **Defense in Depth** — No single control is the last line of defense
2. **Least Privilege** — Every process, user, and service has only the minimum permissions required
3. **Zero Trust** — No implicit trust between services or network zones; all communication is authenticated
4. **Immutable Audit Trail** — All platform actions are logged; the audit log cannot be altered
5. **Fail Secure** — In the event of component failure, the system defaults to a deny/alert state
6. **Separation of Concerns** — The lab/demo environment is completely isolated from any production data

---

## 2. Authentication & Authorization

### 2.1 User Authentication

- Passwords stored as **bcrypt hashes** (cost factor ≥ 12); plaintext passwords never written to disk or logs
- JWT access tokens (RS256 signed, 8-hour expiry)
- JWT refresh tokens (RS256 signed, 7-day expiry, stored in HttpOnly cookie)
- Multi-factor authentication (TOTP via Google Authenticator-compatible apps) — Phase 3
- Account lockout after 5 consecutive failed login attempts (15-minute lockout)
- Session revocation via token JTI blocklist in Redis

### 2.2 Role-Based Access Control (RBAC)

| Role | Permissions |
|---|---|
| `admin` | Full platform access including user management, rule management, system config |
| `analyst` | Read all alerts/events, update alert status, add notes, trigger response actions |
| `readonly` | Read-only access to alerts, assets, and reports; cannot modify any data |

RBAC is enforced at the API layer. Database queries are scoped by role via middleware — an `analyst` cannot reach admin endpoints regardless of request crafting.

### 2.3 Agent Authentication

Agents use a two-part credential:

1. **Installation Token** — A one-time-use token issued during agent provisioning; used to register the agent and obtain a permanent agent token. Expires after 24 hours or first use.
2. **Agent JWT** — A long-lived signed JWT issued at registration. Contains `agent_id`, issued-at, and a per-agent secret claim. Signed with a separate agent signing key (RS256).

Agent tokens are stored hashed (bcrypt) in the `agents` collection. The plaintext token is returned once at registration and never stored again.

Agents communicate exclusively over HTTPS. In production, mutual TLS (mTLS) is required, verifying both agent and server certificates.

---

## 3. Network Security

### 3.1 Service Isolation (Docker)

```
┌─────────────────────────────────────────────────┐
│                  HOST NETWORK                    │
│                                                  │
│  ┌──────────────────────────────────────────┐   │
│  │         public Docker network            │   │
│  │   nginx (443 exposed)  frontend (80)     │   │
│  └────────────────┬─────────────────────────┘   │
│                   │                              │
│  ┌────────────────▼─────────────────────────┐   │
│  │         internal Docker network          │   │
│  │  backend-api  detection-worker           │   │
│  │  mongodb      redis                      │   │
│  │  (NOT accessible from host or internet)  │   │
│  └──────────────────────────────────────────┘   │
└─────────────────────────────────────────────────┘
```

- MongoDB and Redis ports are **never exposed** outside the `internal` Docker network
- The only externally reachable service is **Nginx** on ports 443 (HTTPS) and optionally 80 (redirects to 443)
- All inter-service communication on the `internal` network uses service names as hostnames

### 3.2 TLS Policy

| Connection | Protocol | Notes |
|---|---|---|
| Browser → Nginx | TLS 1.3 | Self-signed cert for lab; CA-signed for production |
| Agent → Backend API | TLS 1.3 + mTLS (production) | Agent cert pinned |
| Backend → MongoDB | TLS 1.2+ | Internal network in lab; TLS required in production |
| Backend → Redis | TLS 1.2+ | Internal network in lab; TLS + AUTH required in production |
| Nginx → Backend | HTTP (internal Docker network only) | Acceptable within trusted Docker network |

### 3.3 Firewall Rules (Production)

- Inbound: Only 443/TCP from internet; 8443/TCP for agent ingestion endpoint
- All other ports blocked at host firewall level
- MongoDB (27017) and Redis (6379) explicitly denied from all external interfaces

---

## 4. Secrets Management

### 4.1 Development / Lab

Secrets stored in `.env` files, which are:
- Listed in `.gitignore` (never committed)
- Provided as an `.env.example` template with placeholder values only
- Loaded by Docker Compose via `env_file` directive

### 4.2 Production

Secrets managed via **HashiCorp Vault** or cloud-native secrets manager (AWS Secrets Manager / Azure Key Vault):
- Application fetches secrets at startup via Vault API using a service role token
- Secrets are injected as environment variables; not written to disk
- Secret rotation supported without application restart (via Vault dynamic secrets)

### 4.3 Secret Inventory

| Secret | Storage | Rotation |
|---|---|---|
| MongoDB connection string | `.env` / Vault | On breach |
| Redis password | `.env` / Vault | On breach |
| JWT signing private key (RS256) | `.env` / Vault | Every 90 days |
| Agent signing private key (RS256) | `.env` / Vault | Every 90 days |
| Agent installation token secret | Generated per-agent | Single use |
| Admin initial password | `.env` / Vault | On first login |

---

## 5. Input Validation & Injection Prevention

- All API request bodies validated via **Pydantic** schemas with strict type enforcement
- String fields have maximum length limits enforced
- Event data fields validated against a per-`event_type` schema before persistence
- All MongoDB queries use **parameterized queries** (PyMongo driver) — no string interpolation in query construction
- IP address fields validated as valid IPv4/IPv6 before storage
- File paths from agents normalized and validated; no path traversal patterns accepted
- Log output sanitized to prevent log injection (newline stripping in logged user-controlled values)

---

## 6. API Security

### 6.1 Rate Limiting

| Endpoint Group | Limit |
|---|---|
| `/auth/login` | 10 requests/minute per IP |
| `/api/v1/ingest` | 1000 requests/minute per agent |
| All other API endpoints | 300 requests/minute per authenticated user |

Rate limit counters stored in Redis with sliding window algorithm. Exceeding limits returns `429 Too Many Requests`.

### 6.2 CORS Policy

- Development: `localhost:3000` allowed
- Production: Only the platform's own domain allowed; no wildcard origins

### 6.3 Security Headers

All responses from Nginx include:

```
Strict-Transport-Security: max-age=63072000; includeSubDomains; preload
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Content-Security-Policy: default-src 'self'; script-src 'self'; ...
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 7. Audit Logging

### 7.1 Events Logged

All of the following generate an `audit_log` record:

| Category | Actions |
|---|---|
| Authentication | Login success, login failure, logout, token refresh, token revocation |
| Alert management | Status change, assignment, note added, false positive marked |
| Response actions | Host isolation, host unisolation, process kill, IP block, account disable |
| Rule management | Rule created, updated, enabled, disabled, deleted |
| User management | User created, role changed, password reset, account locked |
| System | Configuration change, agent registered, agent revoked |

### 7.2 Audit Log Immutability

- The MongoDB user account used by the application has **no update or delete permissions** on the `audit_log` collection
- Audit log documents are append-only
- In production, audit logs are additionally streamed to an external SIEM or write-once object storage

### 7.3 Log Format

All audit records include: `actor_id`, `actor_type`, `action`, `resource_type`, `resource_id`, `details`, `ip_address`, `user_agent`, `created_at`.

Logs are structured JSON — never plaintext — to support automated parsing and alerting.

---

## 8. Container Security

- All service containers run as **non-root** users (dedicated service users in Dockerfiles)
- Container filesystems are read-only where possible; only required directories are writable
- No `privileged: true` or `--cap-add` flags except where strictly required (network sensors)
- Docker socket is not mounted in any service container
- Base images are pinned to specific digest versions (not `latest` tags)
- Container images scanned for known CVEs before deployment (Trivy or Grype in CI pipeline)
- No secrets passed as build args (always runtime environment variables)

---

## 9. Lab Environment Security

The lab environment presents unique risks because it intentionally runs attack tools.

### 9.1 Network Isolation

```
┌─────────────────────────────────────────────────────────────┐
│                     LAB NETWORK (isolated)                   │
│                                                              │
│  ┌──────────────┐         ┌────────────────────────────┐    │
│  │  Kali Linux  │◄───────►│  Victim Container/VM       │    │
│  │  (Attacker)  │         │  (Ubuntu / Windows)        │    │
│  └──────────────┘         └────────────────────────────┘    │
│          │                          │                        │
│          │           ┌──────────────▼──────────┐            │
│          └──────────►│  SentinelXDR Agent      │            │
│                      │  (on victim)            │            │
│                      └──────────────┬──────────┘            │
└─────────────────────────────────────┼──────────────────────┘
                                      │ (events only, no return)
                                      ▼
                         SentinelXDR Backend (host)
```

- Lab network is a dedicated Docker network (`lab_net`) with **no default gateway to internet**
- Kali VM has no route to the SentinelXDR backend directly — only the victim/agent has a route
- The victim container has limited egress (only to SentinelXDR ingestion port on host)
- Attack tools and scripts are never stored in the platform repository; they reside only on the Kali VM

### 9.2 Permitted Lab Attacks

Only the following attack categories are permitted in lab scenarios:

- Local network scanning (nmap against lab network only)
- Exploitation of intentionally vulnerable services on victim container
- Credential brute force against victim services
- Local privilege escalation on victim container
- C2 communication simulation (netcat/socat within lab network)
- File exfiltration simulation (within lab network only)

**Prohibited:**
- Any attack directed at the host machine beyond the lab network
- Attacks against real internet targets
- Denial of service tools
- Ransomware or destructive payload execution

### 9.3 VM Hygiene

- Kali VM is snapshotted before each lab session and restored after
- Victim container is rebuilt from clean image before each scenario
- No sensitive credentials, real data, or production configurations in lab environment

---

## 10. Vulnerability Management

- Dependency updates reviewed weekly; critical CVEs patched within 48 hours
- `pip-audit` and `npm audit` integrated into CI pipeline
- Security-relevant code changes require a peer review before merge
- Penetration testing of the platform itself planned for Phase 3

---

*This security model is the authoritative security policy for SentinelXDR Phase 0.*
