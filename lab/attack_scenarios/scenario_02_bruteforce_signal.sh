#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script does not attempt SSH login. It posts synthetic failed-auth log
# events with simulation markers.

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
      "event_type": "auth_failure",
      "severity": "medium",
      "source": "linux",
      "title": "Safe lab SSH brute force signal",
      "description": "Simulation marker only: repeated failed SSH authentication signals.",
      "raw_event": {
        "message": "Failed password for invalid user labadmin from 192.0.2.10 port 50221 ssh2 [SIMULATION ONLY]",
        "failure_count": 8,
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "auth.user": "labadmin",
        "source.ip": "192.0.2.10",
        "source.port": 50221,
        "auth.service": "ssh",
        "auth.outcome": "failure",
        "failure_count": 8
      },
      "tags": ["lab", "simulation", "ssh", "bruteforce"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 02 Brute Force Signal: synthetic SSH failures (${sim_id})"
post_events_file "${tmp_payload}"
