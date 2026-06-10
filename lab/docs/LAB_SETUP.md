# Lab Setup

This lab is intended for owned, local systems only:

- WSL Ubuntu running the SentinelXDR backend.
- Kali Linux VM as the operator workstation for demonstrations.
- Linux target VM or container with the SentinelXDR Linux Agent installed.

The simulation scripts are safe telemetry generators. They post synthetic events to the backend and do not perform real attacks.

## 1. Backend on WSL Ubuntu

Start the backend according to the main backend README.

Typical local settings:

```bash
cd backend
uvicorn app.main:app --reload
```

Register or log in to an org admin account, then register a lab agent and keep the returned `sxag_...` API key.

## 2. Linux Agent Target

Install and configure the Phase 9 Linux agent on the target VM or container:

```bash
cd agents/linux-agent
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Set the registered lab agent key in `config.yaml` or export:

```bash
export SENTINELXDR_AGENT_API_KEY=sxag_your_registered_lab_agent_key
export SENTINELXDR_API_BASE_URL=http://<wsl-host-ip>:8000
```

Run a safe dry run first:

```bash
python3 -m sentinelxdr_linux_agent --dry-run --once
```

## 3. Kali VM Operator Workstation

The Kali VM is used only to run scripts and validation commands against owned lab services. Do not point these scripts at public systems.

Clone or mount this repository, then export:

```bash
export SENTINELXDR_API_BASE_URL=http://<wsl-host-ip>:8000
export SENTINELXDR_AGENT_API_KEY=sxag_your_registered_lab_agent_key
```

For validation, use a dashboard/API bearer token:

```bash
export SENTINELXDR_TOKEN=eyJ...
```

Alternatively, use local lab login credentials:

```bash
export SENTINELXDR_EMAIL=admin@example.com
export SENTINELXDR_PASSWORD='change-me'
```

## 4. Test Workflow

1. Confirm backend health.
2. Confirm the lab agent key belongs to an enabled agent.
3. Capture a dashboard baseline if desired:

```bash
python3 lab/validation/verify_dashboard.py --write-baseline /tmp/sentinelxdr-dashboard-before.json
```

4. Run a scenario:

```bash
bash lab/attack_scenarios/scenario_06_full_attack_chain.sh
```

5. Validate the expected flow:

```bash
python3 lab/validation/verify_alerts.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_incidents.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_attack_chains.py --scenario scenario_06_full_attack_chain
python3 lab/validation/verify_dashboard.py \
  --scenario scenario_06_full_attack_chain \
  --baseline /tmp/sentinelxdr-dashboard-before.json
```

Expected flow:

```text
Event -> Detection -> Alert -> Incident -> Attack Chain -> Threat Story
```

## Safety Notes

- All scenario payloads include `simulation: true` and `lab`/`simulation` tags.
- Documentation IPs use RFC 5737 test ranges such as `192.0.2.0/24` and `198.51.100.0/24`.
- Scenario scripts do not modify `/etc/cron*`, run `nmap`, attempt SSH authentication, or transfer files.
- Use only on owned local lab systems.
