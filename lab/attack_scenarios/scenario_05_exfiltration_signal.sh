#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script does not transfer data. It posts synthetic network telemetry for
# a large outbound transfer indicator.

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
      "event_type": "network_connection",
      "severity": "high",
      "source": "network",
      "title": "Safe lab large outbound transfer simulation",
      "description": "Simulation marker only: no data transfer occurred.",
      "raw_event": {
        "destination_ip": "198.51.100.25",
        "bytes_sent": 250000000,
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "direction": "outbound",
        "bytes_sent": 250000000,
        "destination.ip": "198.51.100.25"
      },
      "tags": ["lab", "simulation", "exfiltration"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 05 Exfiltration Signal: synthetic outbound transfer telemetry (${sim_id})"
post_events_file "${tmp_payload}"
