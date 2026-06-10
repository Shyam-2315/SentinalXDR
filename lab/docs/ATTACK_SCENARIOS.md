# Attack Scenarios

All scenarios are safe telemetry simulations for owned local lab environments only. They inject synthetic events through the existing agent ingest API and do not execute offensive actions.

## Scenario 01: Reconnaissance

Script: `lab/attack_scenarios/scenario_01_recon.sh`

Purpose: Generate a local-lab network scan signal resembling host discovery and port scanning.

Expected detection:

- `Nmap Scan Detected`
- MITRE `T1595`

Expected SOC output:

- One alert for Nmap scan telemetry.
- One incident for reconnaissance activity.
- One attack chain containing reconnaissance phase and threat-story text.

## Scenario 02: Brute Force Signal

Script: `lab/attack_scenarios/scenario_02_bruteforce_signal.sh`

Purpose: Generate repeated failed SSH authentication signals without attempting any login.

Expected detection:

- `SSH Brute Force Signal`
- MITRE `T1110`

Expected SOC output:

- One alert for SSH brute force signal.
- One incident for credential access.
- One attack chain containing credential access phase and threat-story text.

## Scenario 03: Execution Signal

Script: `lab/attack_scenarios/scenario_03_execution_signal.sh`

Purpose: Generate simulation-marked encoded command telemetry. No command is executed.

Expected detections:

- `Suspicious PowerShell Encoded Command`
- `Suspicious Base64 Command`
- MITRE `T1059.001`
- MITRE `T1027`

Expected SOC output:

- Alerts for encoded PowerShell and base64 command patterns.
- Incidents for execution and defense evasion signals.
- Attack chains with readable stories and recommended actions.

## Scenario 04: Persistence Signal

Script: `lab/attack_scenarios/scenario_04_persistence_signal.sh`

Purpose: Generate cron persistence indicator telemetry without creating or editing cron files.

Expected detection:

- `Linux Cron Persistence`
- MITRE `T1053.003`

Expected SOC output:

- One alert for cron persistence.
- One incident for persistence.
- One attack chain containing persistence phase and cron-focused response actions.

## Scenario 05: Exfiltration Signal

Script: `lab/attack_scenarios/scenario_05_exfiltration_signal.sh`

Purpose: Generate a large outbound transfer indicator without transferring data.

Expected detection:

- `Large Outbound Transfer`
- MITRE `T1041`

Expected SOC output:

- One high-severity alert for outbound transfer.
- One incident for exfiltration.
- One attack chain with exfiltration phase and recommended containment actions.

## Scenario 06: Full Attack Chain

Script: `lab/attack_scenarios/scenario_06_full_attack_chain.sh`

Purpose: Simulate the full local-lab narrative:

```text
Reconnaissance
Credential Access Signal
Execution Signal
Persistence Signal
Exfiltration Signal
```

Expected detections:

- `Nmap Scan Detected`
- `SSH Brute Force Signal`
- `Suspicious PowerShell Encoded Command`
- `Suspicious Base64 Command`
- `Linux Cron Persistence`
- `Large Outbound Transfer`

Expected MITRE techniques:

- `T1595`
- `T1110`
- `T1059.001`
- `T1027`
- `T1053.003`
- `T1041`

Expected SentinelXDR flow:

```text
Event
Detection
Alert
Incident
Attack Chain
Threat Story
```

Implementation note: the current incident engine correlates by agent plus shared MITRE technique or alert title. A full-chain run may produce multiple incidents and attack chains, each with its own MITRE phase, rather than one single incident containing every phase.
