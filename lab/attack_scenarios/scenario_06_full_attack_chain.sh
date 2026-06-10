#!/usr/bin/env bash
set -euo pipefail

# SentinelXDR Attack Simulation Lab
# Safe simulation for owned local lab systems only.
# This script posts one synthetic multi-stage event batch. It does not scan,
# brute force, execute payloads, create persistence, or transfer data.

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
      "title": "Full chain recon simulation",
      "description": "Simulation marker only: local lab reconnaissance stage.",
      "raw_event": {"tool": "nmap-safe-simulation", "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"source.ip": "192.0.2.10", "destination.ip": "192.0.2.20"},
      "tags": ["lab", "simulation", "chain", "recon"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "auth_failure",
      "severity": "medium",
      "source": "linux",
      "title": "Full chain credential access simulation",
      "description": "Simulation marker only: failed SSH signal.",
      "raw_event": {"message": "Failed password for invalid user labadmin from 192.0.2.10 port 50221 ssh2 [SIMULATION ONLY]", "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"auth.user": "labadmin", "source.ip": "192.0.2.10", "auth.service": "ssh", "auth.outcome": "failure"},
      "tags": ["lab", "simulation", "chain", "credential-access"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "process_start",
      "severity": "info",
      "source": "windows",
      "title": "Full chain PowerShell execution simulation",
      "description": "Simulation marker only: encoded command telemetry.",
      "raw_event": {"process_name": "powershell.exe", "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"command_line": "powershell.exe -NoProfile -enc SIMULATION_ONLY_NO_PAYLOAD", "process.command_line": "powershell.exe -NoProfile -enc SIMULATION_ONLY_NO_PAYLOAD"},
      "tags": ["lab", "simulation", "chain", "execution"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "process_start",
      "severity": "info",
      "source": "linux",
      "title": "Full chain base64 execution simulation",
      "description": "Simulation marker only: base64 decode pattern telemetry.",
      "raw_event": {"process_name": "bash", "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"command_line": "echo SIMULATION_ONLY | base64 -d", "process.command_line": "echo SIMULATION_ONLY | base64 -d"},
      "tags": ["lab", "simulation", "chain", "execution"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "file_write",
      "severity": "high",
      "source": "linux",
      "title": "Full chain cron persistence simulation",
      "description": "Simulation marker only: cron file-write indicator.",
      "raw_event": {"path": "/etc/cron.d/sentinelxdr-lab-simulation", "operation": "write", "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"file_path": "/etc/cron.d/sentinelxdr-lab-simulation", "file.path": "/etc/cron.d/sentinelxdr-lab-simulation", "operation": "write"},
      "tags": ["lab", "simulation", "chain", "persistence"],
      "timestamp": "${timestamp}"
    },
    {
      "event_type": "network_connection",
      "severity": "high",
      "source": "network",
      "title": "Full chain exfiltration simulation",
      "description": "Simulation marker only: large outbound transfer indicator.",
      "raw_event": {"destination_ip": "198.51.100.25", "bytes_sent": 250000000, "simulation": true, "simulation_id": "${sim_id}"},
      "normalized_fields": {"direction": "outbound", "bytes_sent": 250000000, "destination.ip": "198.51.100.25"},
      "tags": ["lab", "simulation", "chain", "exfiltration"],
      "timestamp": "${timestamp}"
    }
  ]
}
JSON

echo "[SentinelXDR Lab] Scenario 06 Full Attack Chain: synthetic multi-stage telemetry (${sim_id})"
post_events_file "${tmp_payload}"
