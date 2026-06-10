# Judge Walkthrough

## Problem

Small SOC teams drown in disconnected security events. A failed login, a strange command, a cron change, and a large outbound transfer may each look like separate noise until they are correlated.

## Solution

SentinelXDR is a local-first XDR prototype that ingests telemetry, runs detections, creates alerts, groups them into incidents, builds attack chains, and produces a readable threat story.

## Why It Is Different

- It demonstrates the full security operations workflow, not only a dashboard mockup.
- It has real backend APIs for auth, agents, ingestion, detections, alerts, incidents, attack chains, and dashboard metrics.
- It includes a Linux agent MVP and safe attack simulation lab.
- It maps detections to MITRE ATT&CK techniques.
- It explains what happened in a form a SOC analyst or manager can understand.

## What Happens During An Attack

1. Telemetry arrives from the Linux agent or safe lab simulator.
2. Detection rules match suspicious patterns.
3. Alerts are raised with severity and MITRE mappings.
4. Related alerts become incidents.
5. The correlation engine builds an attack chain.
6. The dashboard shows risk, timeline, graph, and recommended actions.

## Why The VM/Kali Lab Matters

The lab proves the product can be demonstrated repeatably in a controlled environment. It gives judges a safe way to see realistic attacker-style signals without targeting public systems or running destructive code.

## Business Value

SentinelXDR shortens investigation time. Instead of forcing analysts to manually connect raw events, it creates a structured incident and threat story that can drive triage, reporting, and response.
