#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script does not execute encoded commands. It posts synthetic process
# telemetry with benign simulation markers only.

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
      "event_type": "process_start",
      "severity": "info",
      "source": "windows",
      "title": "Safe lab encoded PowerShell simulation",
      "description": "Simulation marker only: no payload executed.",
      "raw_event": {
        "process_name": "powershell.exe",
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "process.name": "powershell.exe",
        "command_line": "powershell.exe -NoProfile -enc SIMULATION_ONLY_NO_PAYLOAD",
        "process.command_line": "powershell.exe -NoProfile -enc SIMULATION_ONLY_NO_PAYLOAD"
      },
      "tags": ["lab", "simulation", "execution", "powershell"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "process_start",
      "severity": "info",
      "source": "linux",
      "title": "Safe lab base64 command simulation",
      "description": "Simulation marker only: command string is telemetry, not executed.",
      "raw_event": {
        "process_name": "bash",
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "process.name": "bash",
        "command_line": "echo SIMULATION_ONLY | base64 -d",
        "process.command_line": "echo SIMULATION_ONLY | base64 -d"
      },
      "tags": ["lab", "simulation", "execution", "base64"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 03 Execution Signal: synthetic encoded-command telemetry (${sim_id})"
post_events_file "${tmp_payload}"
