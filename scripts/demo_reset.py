#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

try:
    from .demo_common import (
        DEMO_AGENT_HOSTNAME,
        DEMO_AGENT_NAME,
        DEMO_EMAIL,
        DEMO_ORGANIZATION,
        DEMO_TAG,
    )
except ImportError:
    from demo_common import (
        DEMO_AGENT_HOSTNAME,
        DEMO_AGENT_NAME,
        DEMO_EMAIL,
        DEMO_ORGANIZATION,
        DEMO_TAG,
    )

DEFAULT_MONGODB_URI = os.environ.get("MONGODB_URI", "mongodb://localhost:27017")
DEFAULT_MONGODB_DATABASE = os.environ.get("MONGODB_DATABASE", "sentinelxdr")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reset SentinelXDR demo-created data only.",
    )
    parser.add_argument("--mongodb-uri", default=DEFAULT_MONGODB_URI)
    parser.add_argument("--mongodb-database", default=DEFAULT_MONGODB_DATABASE)
    parser.add_argument("--yes", action="store_true", help="Confirm deletion of demo-tagged records.")
    args = parser.parse_args()

    if not args.yes:
        print("Refusing to reset without --yes. Only demo-tagged data will be deleted.")
        return 2

    try:
        from pymongo import MongoClient
    except ImportError:
        print("FAIL: pymongo is required for demo_reset.py. It is included with backend deps.", file=sys.stderr)
        return 1

    client = MongoClient(args.mongodb_uri, serverSelectionTimeoutMS=2000)
    db = client[args.mongodb_database]
    try:
        client.admin.command("ping")
    except Exception as exc:  # pragma: no cover - depends on external MongoDB
        print(f"FAIL: unable to reach MongoDB: {exc}", file=sys.stderr)
        return 1

    summary = reset_demo_data(db)
    print("SentinelXDR demo reset complete")
    for collection, count in summary.items():
        print(f"{collection}: deleted {count}")
    return 0


def reset_demo_data(db: Any) -> dict[str, int]:
    demo_events = list(
        db.events.find(
            {
                "$or": [
                    {"tags": DEMO_TAG},
                    {"raw_event.marker": DEMO_TAG},
                    {"raw_event.demo": True},
                ]
            },
            {"id": 1, "agent_id": 1},
        )
    )
    event_ids = [item["id"] for item in demo_events if "id" in item]

    demo_agents = list(
        db.agents.find(
            {
                "$or": [
                    {"tags": DEMO_TAG},
                    {"name": DEMO_AGENT_NAME},
                    {"hostname": DEMO_AGENT_HOSTNAME},
                ]
            },
            {"id": 1},
        )
    )
    agent_ids = [item["id"] for item in demo_agents if "id" in item]

    demo_users = list(db.users.find({"email": DEMO_EMAIL.lower()}, {"id": 1, "organization_id": 1}))
    user_ids = [item["id"] for item in demo_users if "id" in item]
    organization_ids = [item["organization_id"] for item in demo_users if "organization_id" in item]
    demo_orgs = list(db.organizations.find({"name": DEMO_ORGANIZATION}, {"id": 1}))
    organization_ids.extend(item["id"] for item in demo_orgs if "id" in item)

    detection_ids = ids_for(
        db.detection_results.find({"event_id": {"$in": event_ids}}, {"id": 1})
    )
    alert_ids = ids_for(
        db.alerts.find(
            {
                "$or": [
                    {"event_id": {"$in": event_ids}},
                    {"detection_result_id": {"$in": detection_ids}},
                    {"tags": DEMO_TAG},
                ]
            },
            {"id": 1},
        )
    )
    incident_ids = ids_for(
        db.incidents.find(
            {
                "$or": [
                    {"event_ids": {"$in": event_ids}},
                    {"alert_ids": {"$in": alert_ids}},
                    {"agent_ids": {"$in": agent_ids}},
                    {"tags": DEMO_TAG},
                ]
            },
            {"id": 1},
        )
    )

    summary: dict[str, int] = {}
    summary["attack_chains"] = db.attack_chains.delete_many(
        {
            "$or": [
                {"event_ids": {"$in": event_ids}},
                {"alert_ids": {"$in": alert_ids}},
                {"incident_id": {"$in": incident_ids}},
                {"agent_ids": {"$in": agent_ids}},
            ]
        }
    ).deleted_count
    summary["incidents"] = db.incidents.delete_many({"id": {"$in": incident_ids}}).deleted_count
    summary["alerts"] = db.alerts.delete_many({"id": {"$in": alert_ids}}).deleted_count
    summary["detection_results"] = db.detection_results.delete_many(
        {"id": {"$in": detection_ids}}
    ).deleted_count
    summary["events"] = db.events.delete_many({"id": {"$in": event_ids}}).deleted_count
    summary["agents"] = db.agents.delete_many({"id": {"$in": agent_ids}}).deleted_count
    summary["users"] = db.users.delete_many({"id": {"$in": user_ids}}).deleted_count
    summary["organizations"] = db.organizations.delete_many(
        {"id": {"$in": organization_ids}, "name": DEMO_ORGANIZATION}
    ).deleted_count
    return summary


def ids_for(cursor: Any) -> list[str]:
    return [item["id"] for item in cursor if "id" in item]


if __name__ == "__main__":
    raise SystemExit(main())
