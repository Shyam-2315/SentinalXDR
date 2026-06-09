"""Dashboard repository — aggregates data across collections for the dashboard API.

All queries are organisation-scoped.  Simple count-based MongoDB aggregations are
used throughout; there are no full collection scans in the hot path.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

from motor.motor_asyncio import AsyncIOMotorDatabase

from app.models.agent import AgentStatus
from app.models.alert import AlertStatus
from app.models.attack_chain import AttackChainStatus
from app.models.incident import IncidentStatus

# How long (minutes) before an online agent is considered stale
_STALE_THRESHOLD_MINUTES = 5


class DashboardRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self._agents = database["agents"]
        self._events = database["events"]
        self._alerts = database["alerts"]
        self._incidents = database["incidents"]
        self._attack_chains = database["attack_chains"]

    # ------------------------------------------------------------------
    # Counts helpers
    # ------------------------------------------------------------------

    async def _count(self, collection: Any, query: dict[str, Any]) -> int:
        return await collection.count_documents(query)

    # ------------------------------------------------------------------
    # Agent counts
    # ------------------------------------------------------------------

    async def count_agents_by_status(
        self, organization_id: str
    ) -> dict[str, int]:
        """Return a dict with keys: total, online, offline, disabled."""
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
        ]
        result: dict[str, int] = {"online": 0, "offline": 0, "disabled": 0}
        async for doc in self._agents.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        result["total"] = sum(result.values())
        return result

    async def count_stale_agents(self, organization_id: str) -> int:
        """Online agents whose last_seen_at is older than the stale threshold."""
        threshold = datetime.now(UTC) - timedelta(minutes=_STALE_THRESHOLD_MINUTES)
        return await self._count(
            self._agents,
            {
                "organization_id": organization_id,
                "status": AgentStatus.ONLINE.value,
                "last_seen_at": {"$lt": threshold},
            },
        )

    async def count_recently_active_agents(self, organization_id: str) -> int:
        """Online agents with a heartbeat within the last stale threshold window."""
        threshold = datetime.now(UTC) - timedelta(minutes=_STALE_THRESHOLD_MINUTES)
        return await self._count(
            self._agents,
            {
                "organization_id": organization_id,
                "status": AgentStatus.ONLINE.value,
                "last_seen_at": {"$gte": threshold},
            },
        )

    # ------------------------------------------------------------------
    # Event counts
    # ------------------------------------------------------------------

    async def count_events(self, organization_id: str) -> int:
        return await self._count(
            self._events, {"organization_id": organization_id}
        )

    # ------------------------------------------------------------------
    # Alert counts
    # ------------------------------------------------------------------

    async def count_alerts(self, organization_id: str) -> int:
        return await self._count(
            self._alerts, {"organization_id": organization_id}
        )

    async def count_open_alerts(self, organization_id: str) -> int:
        return await self._count(
            self._alerts,
            {
                "organization_id": organization_id,
                "status": AlertStatus.OPEN.value,
            },
        )

    async def count_alerts_by_severity(
        self, organization_id: str
    ) -> dict[str, int]:
        """Return a dict keyed by severity value with alert counts."""
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
        ]
        result: dict[str, int] = {}
        async for doc in self._alerts.aggregate(pipeline):
            result[doc["_id"]] = doc["count"]
        return result

    async def average_attack_chain_risk_score(
        self, organization_id: str
    ) -> float:
        """Mean risk_score across all attack chains for the org; 0.0 if none."""
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            {"$group": {"_id": None, "avg": {"$avg": "$risk_score"}}},
        ]
        async for doc in self._attack_chains.aggregate(pipeline):
            return round(float(doc.get("avg") or 0.0), 2)
        return 0.0

    # ------------------------------------------------------------------
    # Incident counts
    # ------------------------------------------------------------------

    async def count_incidents(self, organization_id: str) -> int:
        return await self._count(
            self._incidents, {"organization_id": organization_id}
        )

    async def count_open_incidents(self, organization_id: str) -> int:
        return await self._count(
            self._incidents,
            {
                "organization_id": organization_id,
                "status": {"$in": [IncidentStatus.OPEN.value, IncidentStatus.INVESTIGATING.value]},
            },
        )

    # ------------------------------------------------------------------
    # Attack chain counts
    # ------------------------------------------------------------------

    async def count_attack_chains(self, organization_id: str) -> int:
        return await self._count(
            self._attack_chains, {"organization_id": organization_id}
        )

    async def count_active_attack_chains(self, organization_id: str) -> int:
        return await self._count(
            self._attack_chains,
            {
                "organization_id": organization_id,
                "status": AttackChainStatus.ACTIVE.value,
            },
        )

    # ------------------------------------------------------------------
    # MITRE aggregation
    # ------------------------------------------------------------------

    async def mitre_tactic_technique_counts(
        self, organization_id: str
    ) -> list[dict[str, Any]]:
        """
        Unwind mitre_tactics and mitre_techniques from alerts, then group by
        (tactic, technique, severity) to return ranked counts.

        Returns list of dicts: {tactic, technique, severity, count}
        """
        pipeline = [
            {"$match": {"organization_id": organization_id}},
            # Only process alerts that have at least one tactic
            {"$match": {"mitre_tactics.0": {"$exists": True}}},
            # Create one document per tactic
            {"$unwind": "$mitre_tactics"},
            # For each tactic, fan out over techniques (or use "" if empty)
            {
                "$addFields": {
                    "technique_list": {
                        "$cond": {
                            "if": {"$gt": [{"$size": {"$ifNull": ["$mitre_techniques", []]}}, 0]},
                            "then": "$mitre_techniques",
                            "else": [""],
                        }
                    }
                }
            },
            {"$unwind": "$technique_list"},
            {
                "$group": {
                    "_id": {
                        "tactic": "$mitre_tactics",
                        "technique": "$technique_list",
                        "severity": "$severity",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"count": -1}},
        ]
        rows: list[dict[str, Any]] = []
        async for doc in self._alerts.aggregate(pipeline):
            rows.append(
                {
                    "tactic": doc["_id"]["tactic"],
                    "technique": doc["_id"]["technique"],
                    "severity": doc["_id"]["severity"],
                    "count": doc["count"],
                }
            )
        return rows

    # ------------------------------------------------------------------
    # Severity trends (last 7 days)
    # ------------------------------------------------------------------

    async def alert_severity_by_day(
        self, organization_id: str, days: int = 7
    ) -> list[dict[str, Any]]:
        """
        Return alert counts grouped by date × severity for the last `days` days.
        Returns list of dicts: {date: "YYYY-MM-DD", severity: str, count: int}
        """
        since = datetime.now(UTC) - timedelta(days=days)
        pipeline = [
            {
                "$match": {
                    "organization_id": organization_id,
                    "created_at": {"$gte": since},
                }
            },
            {
                "$group": {
                    "_id": {
                        "date": {
                            "$dateToString": {
                                "format": "%Y-%m-%d",
                                "date": "$created_at",
                            }
                        },
                        "severity": "$severity",
                    },
                    "count": {"$sum": 1},
                }
            },
            {"$sort": {"_id.date": 1}},
        ]
        rows: list[dict[str, Any]] = []
        async for doc in self._alerts.aggregate(pipeline):
            rows.append(
                {
                    "date": doc["_id"]["date"],
                    "severity": doc["_id"]["severity"],
                    "count": doc["count"],
                }
            )
        return rows
