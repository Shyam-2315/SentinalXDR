#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

try:
    from .demo_common import (
        DEFAULT_API_BASE_URL,
        DEMO_AGENT_HOSTNAME,
        DEMO_AGENT_NAME,
        DEMO_EMAIL,
        DEMO_PASSWORD,
        DEMO_TAG,
        DemoError,
        count_items,
        demo_event_batch,
        get_or_create_demo_auth,
        request_json,
    )
except ImportError:
    from demo_common import (
        DEFAULT_API_BASE_URL,
        DEMO_AGENT_HOSTNAME,
        DEMO_AGENT_NAME,
        DEMO_EMAIL,
        DEMO_PASSWORD,
        DEMO_TAG,
        DemoError,
        count_items,
        demo_event_batch,
        get_or_create_demo_auth,
        request_json,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed SentinelXDR demo data through existing APIs.")
    parser.add_argument("--api-base-url", default=DEFAULT_API_BASE_URL)
    args = parser.parse_args()

    try:
        auth = get_or_create_demo_auth(args.api_base_url)
        token = auth["access_token"]
        agent_response = register_demo_agent(args.api_base_url, token)
        agent_key = agent_response["api_key"]
        ingest_response = request_json(
            args.api_base_url,
            "POST",
            "/api/events/ingest",
            payload={"events": demo_event_batch()},
            agent_key=agent_key,
        )
        summary = request_json(args.api_base_url, "GET", "/api/dashboard/summary", token=token)
        alerts = request_json(args.api_base_url, "GET", "/api/alerts?limit=100", token=token)
        incidents = request_json(args.api_base_url, "GET", "/api/incidents?limit=100", token=token)
        chains = request_json(args.api_base_url, "GET", "/api/attack-chains?limit=100", token=token)
    except DemoError as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    print("SentinelXDR demo seed complete")
    print(f"API base URL: {args.api_base_url}")
    print(f"Demo email: {DEMO_EMAIL}")
    print(f"Demo password: {DEMO_PASSWORD}")
    print(f"Demo tag: {DEMO_TAG}")
    print(f"Demo agent id: {agent_response['agent']['id']}")
    print(f"Demo agent key: {agent_key}")
    print(f"Events accepted: {ingest_response.get('accepted', 0)}")
    print(f"Detections created: {ingest_response.get('detections_created', 0)}")
    print(f"Alerts visible: {count_items(alerts, 'alerts')}")
    print(f"Incidents visible: {count_items(incidents, 'incidents')}")
    print(f"Attack chains visible: {count_items(chains, 'attack_chains')}")
    print(
        "Dashboard totals: "
        f"events={summary.get('total_events', 0)}, "
        f"alerts={summary.get('total_alerts', 0)}, "
        f"incidents={summary.get('total_incidents', 0)}, "
        f"attack_chains={summary.get('total_attack_chains', 0)}"
    )
    print("Safe to rerun: creates another demo-tagged event batch and a demo-tagged agent.")
    return 0


def register_demo_agent(api_base_url: str, token: str) -> dict[str, object]:
    return request_json(
        api_base_url,
        "POST",
        "/api/agents/register",
        payload={
            "name": DEMO_AGENT_NAME,
            "hostname": DEMO_AGENT_HOSTNAME,
            "os_type": "linux",
            "agent_version": "demo-1.0.0",
            "ip_address": "192.0.2.20",
            "tags": [DEMO_TAG, "linux", "lab", "demo"],
        },
        token=token,
    )


if __name__ == "__main__":
    raise SystemExit(main())
