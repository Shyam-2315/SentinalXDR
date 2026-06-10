# SentinelXDR Frontend

Lovable-generated React + Tailwind frontend integrated with the real SentinelXDR backend APIs.

## Configuration

Local API configuration lives in `.env.local`:

```text
VITE_API_BASE_URL=http://localhost:8000
```

## Package Manager

This frontend has `bun.lock`, so Bun is the expected package manager.

```bash
bun install
bun run dev --host 0.0.0.0 --port 5173
bun run build
```

## Integrated Backend APIs

- Auth: login, register, me.
- Dashboard summary, posture, recent alerts/incidents/chains, MITRE summary, trends, agent health.
- Agents list/register/disable.
- Events list/detail.
- Detection rules and results.
- Alerts list/detail/status.
- Incidents list/detail/status/assign/summary.
- Attack chains list/detail/status.

The UI uses real API responses. Empty states remain for empty datasets.
