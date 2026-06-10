# Integration Testing

Use this flow for a full local demo verification.

## 1. Start The Stack

```bash
make dev
```

Expected output:

```text
Backend URL: http://localhost:8000
Frontend URL: http://localhost:5173
Swagger URL: http://localhost:8000/docs
```

## 2. Seed Demo Data

```bash
make demo-seed
```

Save the printed demo email, password, and agent key.

## 3. Open Frontend

Open:

```text
http://localhost:5173
```

Log in with the printed demo credentials.

## 4. Verify Pages

Confirm these pages load real backend data:

- Dashboard
- Agents
- Events
- Alerts
- Incidents
- Attack Chains
- MITRE
- Detection Rules

Expected data:

- Dashboard cards show non-zero demo counts.
- Agents shows the demo Linux agent.
- Events shows `sentinelxdr-demo` events.
- Alerts show MITRE-mapped detections.
- Incidents show correlated cases.
- Attack Chains show story, timeline, graph, risk, and recommended actions.

## 5. Run Lab Scenario

```bash
export SENTINELXDR_API_BASE_URL=http://localhost:8000
export SENTINELXDR_AGENT_API_KEY=<agent key printed by demo_seed.py>
bash lab/attack_scenarios/scenario_06_full_attack_chain.sh
```

## 6. Refresh Dashboard

Refresh the frontend dashboard. Counts should increase and recent alerts/incidents/chains should update.

## 7. Run Checks

```bash
make check
make demo-smoke
```

## Cleanup

```bash
make stop
python3 scripts/demo_reset.py --yes --mongodb-uri mongodb://localhost:27017
```

`demo_reset.py` only removes demo-tagged/demo-identified records.
