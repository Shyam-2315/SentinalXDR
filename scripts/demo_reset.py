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
    demo_users = list(
        db.users.find({"email": DEMO_EMAIL.lower()}, {"id": 1, "organization_id": 1})
    )
    user_ids = ids_for(demo_users)
    candidate_organization_ids = {
        item["organization_id"] for item in demo_users if "organization_id" in item
    }
    demo_orgs = list(db.organizations.find({"name": DEMO_ORGANIZATION}, {"id": 1}))
    candidate_organization_ids.update(ids_for(demo_orgs))

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
    agent_ids = ids_for(demo_agents)

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
    event_ids = ids_for(demo_events)

    detection_ids = ids_for(
        db.detection_results.find(
            {
                "$or": [
                    {"event_id": {"$in": event_ids}},
                    {"agent_id": {"$in": agent_ids}},
                ]
            },
            {"id": 1},
        )
    )
    alert_ids = ids_for(
        db.alerts.find(
            {
                "$or": [
                    {"event_id": {"$in": event_ids}},
                    {"detection_result_id": {"$in": detection_ids}},
                    {"agent_id": {"$in": agent_ids}},
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
                    {"detection_result_ids": {"$in": detection_ids}},
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
                {"detection_result_ids": {"$in": detection_ids}},
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
    organization_ids = safe_demo_organization_ids(
        db,
        organization_ids=list(candidate_organization_ids),
        user_ids=user_ids,
        agent_ids=agent_ids,
        event_ids=event_ids,
        detection_ids=detection_ids,
        alert_ids=alert_ids,
        incident_ids=incident_ids,
    )
    summary["organizations"] = db.organizations.delete_many(
        {"id": {"$in": organization_ids}, "name": DEMO_ORGANIZATION}
    ).deleted_count
    return summary


def ids_for(cursor: Any) -> list[str]:
    return [item["id"] for item in cursor if "id" in item]


def safe_demo_organization_ids(
    db: Any,
    *,
    organization_ids: list[str],
    user_ids: list[str],
    agent_ids: list[str],
    event_ids: list[str],
    detection_ids: list[str],
    alert_ids: list[str],
    incident_ids: list[str],
) -> list[str]:
    safe_ids: list[str] = []
    for organization_id in organization_ids:
        if not has_non_demo_records(
            db,
            organization_id=organization_id,
            user_ids=user_ids,
            agent_ids=agent_ids,
            event_ids=event_ids,
            detection_ids=detection_ids,
            alert_ids=alert_ids,
            incident_ids=incident_ids,
        ):
            safe_ids.append(organization_id)
    return safe_ids


def has_non_demo_records(
    db: Any,
    *,
    organization_id: str,
    user_ids: list[str],
    agent_ids: list[str],
    event_ids: list[str],
    detection_ids: list[str],
    alert_ids: list[str],
    incident_ids: list[str],
) -> bool:
    checks = [
        (db.users, user_ids),
        (db.agents, agent_ids),
        (db.events, event_ids),
        (db.detection_results, detection_ids),
        (db.alerts, alert_ids),
        (db.incidents, incident_ids),
    ]
    for collection, demo_ids in checks:
        if collection.count_documents(
            {"organization_id": organization_id, "id": {"$nin": demo_ids}},
        ):
            return True

    if db.attack_chains.count_documents(
        {
            "organization_id": organization_id,
            "incident_id": {"$nin": incident_ids},
            "event_ids": {"$nin": event_ids},
            "alert_ids": {"$nin": alert_ids},
            "detection_result_ids": {"$nin": detection_ids},
            "agent_ids": {"$nin": agent_ids},
        },
    ):
        return True

    return bool(db.detection_rules.count_documents({"organization_id": organization_id}))


if __name__ == "__main__":
    raise SystemExit(main())
