# SentinelXDR Attack Simulation Lab

Safe cyber range assets for local SentinelXDR demonstrations.

This lab is for owned, isolated lab systems only. The scenario scripts do not scan networks, brute force services, exploit software, create persistence, or transfer data. They inject simulation-marked telemetry into the existing SentinelXDR backend through `POST /api/events/ingest` using a registered lab agent API key.

## Structure

```text
lab/
  attack_scenarios/      Safe telemetry simulation scripts
  validation/            API validation utilities
  docs/                  Setup, scenarios, and detection mapping
  scenario_metadata.json Shared scenario expectations
  tests/                 Unit tests for validation and metadata
```

## Quick Start

```bash
export SENTINELXDR_API_BASE_URL=http://localhost:8000
export SENTINELXDR_AGENT_API_KEY=sxag_your_registered_lab_agent_key

bash lab/attack_scenarios/scenario_06_full_attack_chain.sh
```

Validate with either a bearer token:

```bash
export SENTINELXDR_TOKEN=eyJ...
python3 lab/validation/verify_alerts.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_incidents.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_attack_chains.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_dashboard.py --scenario scenario_06_full_attack_chain
```

Or with login credentials:

```bash
export SENTINELXDR_EMAIL=admin@example.com
export SENTINELXDR_PASSWORD='change-me'
python3 lab/validation/verify_alerts.py --scenario scenario_01_recon
```

See [LAB_SETUP.md](docs/LAB_SETUP.md), [ATTACK_SCENARIOS.md](docs/ATTACK_SCENARIOS.md), and [DETECTION_MAPPING.md](docs/DETECTION_MAPPING.md).
