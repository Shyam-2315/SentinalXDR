#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script does not create or modify cron jobs. It posts synthetic file-write
# telemetry for cron persistence indicators.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lab/attack_scenarios/lib.sh
source "${SCRIPT_DIR}/lib.sh"

tmp_payload="$(mktemp)"
trap 'rm -f "${tmp_payload}"' EXIT

timestamp="$(lab_timestamp)"
sim_id="$(simulation_id)"

cat >"${tmp_payload}" <<JSON
{
  "events": [
    {
      "event_type": "file_write",
      "severity": "high",
      "source": "linux",
      "title": "Safe lab cron persistence simulation",
      "description": "Simulation marker only: cron persistence indicator, no file modified.",
      "raw_event": {
        "path": "/etc/cron.d/sentinelxdr-lab-simulation",
        "operation": "write",
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "file_path": "/etc/cron.d/sentinelxdr-lab-simulation",
        "file.path": "/etc/cron.d/sentinelxdr-lab-simulation",
        "operation": "write"
      },
      "tags": ["lab", "simulation", "persistence", "cron"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 04 Persistence Signal: synthetic cron telemetry (${sim_id})"
post_events_file "${tmp_payload}"
