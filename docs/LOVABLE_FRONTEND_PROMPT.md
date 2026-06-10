# Lovable Frontend Prompt

Build a production-quality React + Tailwind frontend for SentinelXDR using the existing backend APIs only. Do not invent backend endpoints.

Use a dark SOC dashboard style: dense, clear, professional, and investigation-focused. Avoid marketing hero pages. The first screen after login should be the usable dashboard.

## Backend

Use an environment variable for the API base URL:

```text
VITE_API_BASE_URL=http://localhost:8000
```

Implement JWT auth handling:

- Login with `POST /api/auth/login`.
- Store the access token.
- Send `Authorization: Bearer <token>` for protected APIs.
- Redirect unauthenticated users to `/login`.
- Handle 401 by clearing auth state.

## Pages

Create these routes:

- `/login`
- `/dashboard`
- `/agents`
- `/events`
- `/alerts`
- `/incidents`
- `/attack-chains`
- `/attack-chains/:id`
- `/mitre`

## Required Views

Login page:

- Email/password form.
- Error state.
- Loading state.

Dashboard:

- Cards for total agents, online agents, total events, total alerts, open alerts, total incidents, open incidents, total attack chains, active attack chains, average risk.
- Security posture panel.
- Recent alerts.
- Recent incidents.
- Recent attack chains.
- Severity trends chart.
- MITRE summary chart.
- Agent health widget.

Agents:

- Table with hostname, OS type, version, status, IP, last seen, tags.

Events:

- Filterable table with timestamp, source, event type, severity, title, agent id, tags.
- Detail drawer showing raw event and normalized fields as JSON.

Alerts:

- Table with title, severity, status, MITRE tactics, MITRE techniques, tags, created time.
- Severity and status badges.

Incidents:

- Table with title, severity, status, MITRE techniques, first seen, last seen, assigned user.
- Incident detail view with alert ids, event ids, summary, tags.

Attack Chains:

- List page with title, severity, risk score, confidence score, status, MITRE techniques, first/last seen.
- Detail page with threat story view, recommended actions, timeline, and graph view.
- Graph nodes use backend `graph.nodes`; edges use backend `graph.edges`.

MITRE Summary:

- Tactic and technique coverage from `/api/dashboard/mitre-summary`.

## Components

Use cards, tables, charts, badges, tabs, filters, drawers, and graph view. Use icons where appropriate. Keep the interface compact and SOC-oriented.

## API Context

Read `docs/lovable_context.json` and `docs/FRONTEND_API_EXAMPLES.md` for endpoint examples and response shapes.
