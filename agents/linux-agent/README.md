# SentinelXDR Linux Agent MVP

Production-clean Linux telemetry agent for SentinelXDR Phase 9. The agent is read-only: it reads local logs, process metadata, cron file metadata, and host metadata, then sends normalized events to the existing backend ingestion API.

## What it collects

- SSH failed login signals from `/var/log/auth.log` or `/var/log/secure` when readable.
- sudo usage signals from auth logs.
- cron modification signals from configured cron files/directories.
- process snapshot via `psutil`.
- system metadata including hostname, OS details, and non-loopback IP addresses.

All emitted events use the backend Phase 4 event shape:

```json
{
  "event_type": "auth_failure",
  "severity": "medium",
  "source": "linux",
  "title": "SSH failed login",
  "description": "Failed SSH authentication - root - 203.0.113.10",
  "raw_event": {},
  "normalized_fields": {},
  "tags": ["auth", "ssh", "linux"],
  "timestamp": "2026-06-10T12:00:00Z"
}
```

## Setup

```bash
cd agents/linux-agent
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp config.yaml.example config.yaml
```

Register an agent using the backend API or admin workflow, then put the returned existing API key in `config.yaml`:

```yaml
api:
  base_url: http://localhost:8000

agent:
  api_key: sxag_replace_with_registered_agent_key
```

The agent sends:

- `POST /api/agents/heartbeat` with `X-Agent-Key`
- `POST /api/events/ingest` with `X-Agent-Key`

No backend API changes are required.

## Configuration

The agent loads `config.yaml` first, then environment variables override file values.

Supported environment variables:

- `SENTINELXDR_API_BASE_URL`
- `SENTINELXDR_AGENT_API_KEY`
- `SENTINELXDR_AGENT_VERSION`
- `SENTINELXDR_INTERVAL_SECONDS`
- `SENTINELXDR_BATCH_SIZE`
- `SENTINELXDR_DRY_RUN`
- `SENTINELXDR_ONCE`
- `SENTINELXDR_TIMEOUT_SECONDS`
- `SENTINELXDR_MAX_RETRIES`
- `SENTINELXDR_BACKOFF_SECONDS`
- `SENTINELXDR_STATE_PATH`
- `SENTINELXDR_LOG_LEVEL`
- `SENTINELXDR_AUTH_LOG_PATHS` comma-separated
- `SENTINELXDR_CRON_PATHS` comma-separated
- `SENTINELXDR_PROCESS_LIMIT`
- `SENTINELXDR_INITIAL_LOG_TAIL_BYTES`

## Usage

Dry-run once, printing events without network calls:

```bash
python -m sentinelxdr_linux_agent --config config.yaml --dry-run --once
```

Run one live collection cycle:

```bash
python -m sentinelxdr_linux_agent --config config.yaml --once
```

Run continuously:

```bash
python -m sentinelxdr_linux_agent --config config.yaml
```

Override selected values:

```bash
SENTINELXDR_AGENT_API_KEY=sxag_... \
SENTINELXDR_API_BASE_URL=http://localhost:8000 \
python -m sentinelxdr_linux_agent --once
```

## Operational Notes

- Auth logs often require root or group permissions to read. If unavailable, the agent logs a warning and continues collecting other telemetry.
- The state file stores log offsets and cron file mtimes to avoid replaying the same signals in loop mode.
- On first log read, the agent tails the configured log files instead of ingesting full historical logs.
- Network errors and backend 5xx responses are retried with exponential backoff. Backend 4xx responses fail fast because they usually indicate bad configuration or authorization.

## Tests

```bash
cd agents/linux-agent
pytest
```
