# Frontend API Examples

Set:

```ts
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL;
```

## Login

```ts
const res = await fetch(`${API_BASE_URL}/api/auth/login`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ email, password }),
});
const data = await res.json();
localStorage.setItem("access_token", data.access_token);
```

## Authenticated GET Helper

```ts
async function apiGet(path: string) {
  const token = localStorage.getItem("access_token");
  const res = await fetch(`${API_BASE_URL}${path}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
```

## `/api/dashboard/summary`

```json
{
  "total_agents": 1,
  "online_agents": 1,
  "offline_agents": 0,
  "disabled_agents": 0,
  "total_events": 6,
  "total_alerts": 6,
  "open_alerts": 6,
  "total_incidents": 6,
  "open_incidents": 6,
  "total_attack_chains": 6,
  "active_attack_chains": 6,
  "critical_alerts": 0,
  "high_alerts": 2,
  "risk_score_average": 72.5
}
```

## `/api/dashboard/security-posture`

```json
{
  "posture_score": 58,
  "posture_label": "moderate",
  "top_risks": ["2 high-severity alert(s) unresolved"],
  "recommended_actions": ["Review and close high-severity alerts"]
}
```

## `/api/alerts`

```json
{
  "alerts": [
    {
      "id": "alr_...",
      "title": "SSH Brute Force Signal",
      "description": "Linux authentication log indicates repeated SSH failures.",
      "severity": "medium",
      "status": "open",
      "mitre_tactics": ["Credential Access"],
      "mitre_techniques": ["T1110"],
      "tags": ["ssh", "bruteforce"],
      "created_at": "2026-06-10T12:00:00Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "skip": 0
}
```

## `/api/incidents`

```json
{
  "incidents": [
    {
      "id": "inc_...",
      "title": "SSH Brute Force Signal",
      "severity": "medium",
      "status": "open",
      "alert_ids": ["alr_..."],
      "event_ids": ["evt_..."],
      "agent_ids": ["agt_..."],
      "mitre_tactics": ["Credential Access"],
      "mitre_techniques": ["T1110"],
      "first_seen_at": "2026-06-10T12:00:00Z",
      "last_seen_at": "2026-06-10T12:00:00Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "skip": 0
}
```

## `/api/attack-chains`

```json
{
  "attack_chains": [
    {
      "id": "chain_...",
      "title": "Attack chain: SSH Brute Force Signal",
      "severity": "medium",
      "risk_score": 51,
      "confidence_score": 52,
      "kill_chain_phases": ["credential_access"],
      "mitre_tactics": ["Credential Access"],
      "mitre_techniques": ["T1110"],
      "story": "SentinelXDR observed suspicious activity on host demo-linux-target...",
      "recommended_actions": ["reset credentials", "inspect LSASS/auth logs"],
      "graph": {
        "nodes": [{"id": "agt_...", "label": "demo-linux-target", "type": "agent"}],
        "edges": []
      }
    }
  ],
  "count": 1,
  "limit": 100,
  "skip": 0
}
```

## `/api/events`

```json
{
  "events": [
    {
      "id": "evt_...",
      "agent_id": "agt_...",
      "event_type": "auth_failure",
      "severity": "medium",
      "source": "linux",
      "title": "Demo SSH brute force signal",
      "raw_event": {"marker": "sentinelxdr-demo"},
      "normalized_fields": {"auth.service": "ssh"},
      "tags": ["sentinelxdr-demo"],
      "timestamp": "2026-06-10T12:00:00Z",
      "received_at": "2026-06-10T12:00:01Z"
    }
  ],
  "count": 1,
  "limit": 100,
  "skip": 0
}
```

## `/api/agents`

```json
{
  "agents": [
    {
      "id": "agt_...",
      "name": "sentinelxdr-demo-linux-agent",
      "hostname": "demo-linux-target",
      "os_type": "linux",
      "agent_version": "demo-1.0.0",
      "status": "online",
      "last_seen_at": "2026-06-10T12:00:01Z",
      "ip_address": "192.0.2.20",
      "tags": ["sentinelxdr-demo", "linux", "lab", "demo"]
    }
  ]
}
```
