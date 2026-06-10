# SentinelXDR Demo Script

## 1. Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

Confirm the API is reachable:

```bash
curl http://localhost:8000/health/live
curl http://localhost:8000/health/ready
```

## 2. Seed Demo Data

From the repository root:

```bash
python3 scripts/demo_seed.py --api-base-url http://localhost:8000
```

The script prints:

- Demo user email and password.
- API base URL.
- Demo Linux agent key.
- Accepted event count.
- Visible alerts, incidents, attack chains, and dashboard totals.

All seeded events are safe simulation telemetry tagged with `sentinelxdr-demo`.

## 3. Run Smoke Check

```bash
python3 scripts/demo_smoke_check.py --api-base-url http://localhost:8000
```

Expected output:

```text
PASS backend live
PASS backend ready
PASS auth works
PASS dashboard summary works
PASS recent alerts works
PASS recent incidents works
PASS attack chains works
```

## 4. Run Attack Scenario

For the full safe cyber-range story:

```bash
export SENTINELXDR_API_BASE_URL=http://localhost:8000
export SENTINELXDR_AGENT_API_KEY=<agent key printed by demo_seed.py>
bash lab/attack_scenarios/scenario_06_full_attack_chain.sh
```

This posts simulation-marked telemetry for reconnaissance, credential access, execution, persistence, and exfiltration.

## 5. Show Dashboard

Use the backend API today, and later the Lovable frontend:

```bash
python3 scripts/demo_smoke_check.py
python3 lab/validation/verify_alerts.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_incidents.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_attack_chains.py --scenario scenario_06_full_attack_chain
```

## 6. Explain The Flow

```text
Agent or lab telemetry
Event ingestion
Detection Engine rule match
Alert creation
Incident correlation
Attack Chain graph and timeline
Threat Story with recommended actions
Dashboard metrics
```

The key message: SentinelXDR does not just store logs. It turns endpoint and network signals into an investigation-ready story.
