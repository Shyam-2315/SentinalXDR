#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation helper for owned local lab systems only.
# This library posts synthetic telemetry to the local SentinelXDR backend.
# It does not scan, brute force, exploit, exfiltrate, or modify target systems.

LAB_API_BASE_URL="${SENTINELXDR_API_BASE_URL:-http://localhost:8000}"
LAB_AGENT_API_KEY="${SENTINELXDR_AGENT_API_KEY:-}"

require_lab_config() {
  if [[ -z "${LAB_AGENT_API_KEY}" ]]; then
    echo "ERROR: SENTINELXDR_AGENT_API_KEY must be set to an existing lab agent key." >&2
    exit 2
  fi
}

lab_timestamp() {
  date -u +"%Y-%m-%dT%H:%M:%SZ"
}

simulation_id() {
  date -u +"sim-%Y%m%dT%H%M%SZ"
}

post_events_file() {
  local payload_file="$1"

  require_lab_config
  echo "[SentinelXDR Lab] Posting synthetic event batch to ${LAB_API_BASE_URL}/api/events/ingest"
  curl --fail-with-body --silent --show-error \
    --request POST "${LAB_API_BASE_URL}/api/events/ingest" \
    --header "X-Agent-Key: ${LAB_AGENT_API_KEY}" \
    --header "Content-Type: application/json" \
    --data @"${payload_file}"
  echo
}
