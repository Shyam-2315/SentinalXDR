# Detection Mapping

| Scenario | Event Shape | Detection Rule | MITRE Tactic | MITRE Technique |
|---|---|---|---|---|
| Scenario 01 Reconnaissance | `network_scan`, `source=network`, `raw_event.tool` contains `nmap` | Nmap Scan Detected | Reconnaissance | T1595 |
| Scenario 02 Brute Force Signal | `auth_failure`, `source=linux`, `raw_event.message` contains `Failed password` | SSH Brute Force Signal | Credential Access | T1110 |
| Scenario 03 Execution Signal | `process_start`, `source=windows`, `normalized_fields.command_line` contains `powershell` and `-enc` | Suspicious PowerShell Encoded Command | Execution | T1059.001 |
| Scenario 03 Execution Signal | `process_start`, `source=linux`, `normalized_fields.command_line` contains `base64` and `-d` | Suspicious Base64 Command | Defense Evasion | T1027 |
| Scenario 04 Persistence Signal | `file_write`, `source=linux`, `normalized_fields.file_path` contains `/cron` | Linux Cron Persistence | Persistence | T1053.003 |
| Scenario 05 Exfiltration Signal | `network_connection`, `source=network`, outbound direction and `bytes_sent >= 100000000` | Large Outbound Transfer | Exfiltration | T1041 |
| Scenario 06 Full Attack Chain | Combined safe telemetry batch | All listed rules | Multiple | T1595, T1110, T1059.001, T1027, T1053.003, T1041 |

## Safety Markers

Every scenario event includes:

- `raw_event.simulation: true`
- `raw_event.simulation_id`
- `tags` containing `lab` and `simulation`

These markers make lab telemetry easy to identify during investigations and cleanup.
