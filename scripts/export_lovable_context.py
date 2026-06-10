#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from .demo_common import DEFAULT_API_BASE_URL
except ImportError:
    from demo_common import DEFAULT_API_BASE_URL

OUTPUT_PATH = Path("docs/lovable_context.json")


def build_lovable_context(api_base_url: str = DEFAULT_API_BASE_URL) -> dict[str, object]:
    return {
        "project": "SentinelXDR",
        "api_base_url": api_base_url,
        "auth_flow": {
            "type": "JWT bearer",
            "login_endpoint": "POST /api/auth/login",
            "register_endpoint": "POST /api/auth/register",
            "refresh_endpoint": "POST /api/auth/refresh",
            "storage": "Store access token client-side and send Authorization: Bearer <token>.",
        },
        "endpoints": [
            "POST /api/auth/login",
            "GET /api/auth/me",
            "GET /api/dashboard/summary",
            "GET /api/dashboard/security-posture",
            "GET /api/dashboard/recent-alerts",
            "GET /api/dashboard/recent-incidents",
            "GET /api/dashboard/recent-attack-chains",
            "GET /api/dashboard/mitre-summary",
            "GET /api/dashboard/severity-trends",
            "GET /api/dashboard/agent-health",
            "GET /api/agents",
            "GET /api/events",
            "GET /api/alerts",
            "GET /api/incidents",
            "GET /api/attack-chains",
        ],
        "response_examples": response_examples(),
        "page_plan": [
            {"route": "/login", "purpose": "JWT login screen"},
            {"route": "/dashboard", "purpose": "SOC overview, posture, metrics, trends"},
            {"route": "/agents", "purpose": "Agent inventory and health"},
            {"route": "/events", "purpose": "Searchable event stream"},
            {"route": "/alerts", "purpose": "Alert triage queue"},
            {"route": "/incidents", "purpose": "Incident management"},
            {"route": "/attack-chains", "purpose": "Correlated attack-chain list"},
            {"route": "/attack-chains/:id", "purpose": "Threat story, timeline, graph view"},
            {"route": "/mitre", "purpose": "MITRE tactic and technique summary"},
        ],
        "ui_components_needed": [
            "Login form",
            "Metric cards",
            "Severity trend chart",
            "MITRE coverage chart",
            "Agent health table",
            "Alerts table",
            "Incidents table",
            "Events table",
            "Attack chain graph",
            "Attack timeline",
            "Threat story panel",
            "Status and severity badges",
            "Filter/search controls",
        ],
        "dashboard_card_fields": [
            "total_agents",
            "online_agents",
            "total_events",
            "total_alerts",
            "open_alerts",
            "total_incidents",
            "open_incidents",
            "total_attack_chains",
            "active_attack_chains",
            "risk_score_average",
        ],
        "alert_table_fields": [
            "title",
            "severity",
            "status",
            "mitre_tactics",
            "mitre_techniques",
            "created_at",
        ],
        "incident_table_fields": [
            "title",
            "severity",
            "status",
            "mitre_techniques",
            "first_seen_at",
            "last_seen_at",
            "assigned_to_user_id",
        ],
        "attack_chain_graph_fields": [
            "graph.nodes[].id",
            "graph.nodes[].label",
            "graph.nodes[].type",
            "graph.nodes[].severity",
            "graph.edges[].source",
            "graph.edges[].target",
            "graph.edges[].relationship",
        ],
        "recommended_frontend_routes": [
            "/login",
            "/dashboard",
            "/agents",
            "/events",
            "/alerts",
            "/incidents",
            "/attack-chains",
            "/attack-chains/:id",
            "/mitre",
        ],
    }


def response_examples() -> dict[str, object]:
    return {
        "login": {
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "token_type": "bearer",
            "user": {"email": "demo@sentinelxdrdemo.com", "role": "org_admin"},
        },
        "dashboard_summary": {
            "total_agents": 1,
            "online_agents": 1,
            "total_events": 6,
            "total_alerts": 6,
            "open_alerts": 6,
            "total_incidents": 6,
            "total_attack_chains": 6,
            "risk_score_average": 72.5,
        },
        "alert": {
            "id": "alr_...",
            "title": "SSH Brute Force Signal",
            "severity": "medium",
            "status": "open",
            "mitre_techniques": ["T1110"],
        },
        "attack_chain": {
            "id": "chain_...",
            "title": "Attack chain: SSH Brute Force Signal",
            "story": "SentinelXDR observed suspicious activity...",
            "graph": {"nodes": [], "edges": []},
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Export Lovable.dev frontend context.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    parser.add_argument("--output", default=str(OUTPUT_PATH))
    args = parser.parse_args()

    context = build_lovable_context(args.api_base_url)
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Wrote Lovable context to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
