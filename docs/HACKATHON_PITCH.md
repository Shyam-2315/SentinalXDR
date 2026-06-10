# Hackathon Pitch

## 2-Minute Pitch

Security teams do not need more raw alerts. They need context.

SentinelXDR is a local-first XDR platform that turns endpoint and network telemetry into detections, alerts, incidents, attack chains, and readable threat stories. In this demo, a Linux agent and safe attack simulation lab generate realistic signals: reconnaissance, SSH brute force, suspicious command execution, cron persistence, and exfiltration indicators.

The backend correlates those events automatically. Judges can see the full flow from event ingestion to MITRE-mapped alert, incident, attack-chain graph, and threat story. This shows not just detection, but investigation readiness.

## 5-Minute Pitch

SentinelXDR solves a common SOC problem: fragmented signals. A scan, failed SSH logins, encoded commands, persistence, and outbound transfer can look unrelated when viewed as raw logs. SentinelXDR connects them.

The platform includes:

- JWT auth and organization-scoped APIs.
- Agent registration and heartbeat.
- Event ingestion using agent API keys.
- Built-in detection rules.
- Alert generation.
- Incident correlation.
- Attack-chain engine with graph, timeline, risk, confidence, and story.
- Dashboard APIs.
- Linux Agent MVP.
- Safe local attack simulation lab.

The demo is fully local: WSL Ubuntu backend, Kali VM operator, and Linux target or container. No public targets, no exploit code, no destructive actions.

The result is a product narrative recruiters and judges can understand: SentinelXDR turns telemetry into decisions.

## Winning Differentiators

- End-to-end backend, not only UI screens.
- Safe cyber-range demo with repeatable scenarios.
- MITRE ATT&CK mapping.
- Threat-story generation without external AI calls.
- Clean API contracts ready for Lovable frontend generation.
- Practical Linux agent MVP.

## Future Roadmap

- Lovable.dev React + Tailwind frontend.
- More agent collectors and Windows agent support.
- Custom detection rule editor UI.
- Case management workflows.
- Report export.
- Response playbooks with safe approval gates.
- Multi-tenant production hardening.
