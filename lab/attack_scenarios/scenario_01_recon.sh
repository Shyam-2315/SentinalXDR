#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script does not run nmap or scan any network. It posts synthetic
# reconnaissance telemetry that resembles local-lab port scanning.

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
      "event_type": "network_scan",
      "severity": "medium",
      "source": "network",
      "title": "Safe lab reconnaissance simulation",
      "description": "Simulation marker only: local lab host discovery and port scan telemetry.",
      "raw_event": {
        "tool": "nmap-safe-simulation",
        "scan_type": "tcp_connect",
        "target_scope": "owned-local-lab-only",
        "ports": [22, 80, 443, 8000],
        "simulation": true,
        "simulation_id": "${sim_id}"
      },
      "normalized_fields": {
        "source.ip": "192.0.2.10",
        "destination.ip": "192.0.2.20",
        "port.count": 4
      },
      "tags": ["lab", "simulation", "recon", "nmap"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 01 Reconnaissance: synthetic local-lab scan signal (${sim_id})"
post_events_file "${tmp_payload}"
