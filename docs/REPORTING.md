# SentinelXDR Reporting

Phase 16 adds professional report exports for SOC investigation, compliance review, and executive communication.

## Endpoints

All endpoints require a bearer access token and are organization-scoped.

| Method | Path | Format | Audit action |
| --- | --- | --- | --- |
| `GET` | `/api/reports/incidents/{incident_id}.pdf` | PDF | `report.incident_export` |
| `GET` | `/api/reports/attack-chains/{chain_id}.pdf` | PDF | `report.attack_chain_export` |
| `GET` | `/api/reports/evidence/{evidence_id}.pdf` | PDF | `report.evidence_export` |
| `GET` | `/api/reports/audit.csv` | CSV | `report.audit_export` |
| `GET` | `/api/reports/executive-summary.pdf` | PDF | `report.executive_summary_export` |

The same routes are also available under the configured versioned API prefix.

## RBAC

- `VIEWER` can export read-only PDF reports for incidents, attack chains, evidence, and executive summaries.
- `ANALYST`, `ORG_ADMIN`, and `SUPER_ADMIN` can export all report types, including audit CSV.
- Exports only return records belonging to the current user's organization. Cross-organization IDs return `404`.

## Report Contents

PDF reports include:

- Organization name.
- Generated-by user and generated timestamp.
- Incident, attack-chain, or evidence details.
- MITRE tactics and techniques.
- Linked alert references.
- Evidence SHA-256 hashes and verification state.
- Chain-of-custody events.
- Related audit references.
- Recommended actions.

Audit CSV includes:

- Audit ID.
- Organization ID.
- Timestamp.
- Actor email and role.
- Action.
- Resource type and resource ID.
- Status.
- IP address.
- Description.

## Frontend

The Reports page is available at `/reports` and exposes executive summary export. Detail pages expose context-specific exports:

- Incident detail: Export PDF.
- Attack chain detail: Export PDF.
- Evidence detail sheet: Export PDF.
- Audit logs: Export CSV.

Downloads use authenticated `fetch`, read `Content-Disposition`, create a browser object URL, and trigger a file download.

## Limitations

- Reports are generated on demand; scheduled delivery is not implemented.
- Audit CSV exports the latest 5,000 organization-scoped audit rows.
- PDF templates are text/table based and do not embed attack graph images.
- Report exports are not stored as evidence artifacts automatically.
