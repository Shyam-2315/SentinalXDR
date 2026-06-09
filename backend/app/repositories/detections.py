from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from motor.motor_asyncio import AsyncIOMotorDatabase
from pymongo import ReturnDocument

from app.models.detection import DetectionResult, DetectionRule
from app.models.event import Event, EventSeverity, EventSource


def builtin_detection_rules() -> list[DetectionRule]:
    now = datetime.now(UTC)
    return [
        DetectionRule(
            id="builtin_suspicious_powershell_encoded_command",
            name="Suspicious PowerShell Encoded Command",
            description="PowerShell command line includes encoded-command usage.",
            severity=EventSeverity.HIGH,
            source=EventSource.WINDOWS,
            event_type="process_start",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "contains",
                        "value": "powershell",
                    },
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "contains",
                        "value": "-enc",
                    },
                ],
            },
            mitre_tactics=["Execution"],
            mitre_techniques=["T1059.001"],
            tags=["powershell", "encoded-command"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_possible_mimikatz_execution",
            name="Possible Mimikatz Execution",
            description="Command line or process name contains Mimikatz indicators.",
            severity=EventSeverity.CRITICAL,
            source=EventSource.WINDOWS,
            event_type="process_start",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "regex",
                        "value": "mimikatz|sekurlsa|lsadump",
                    },
                ],
            },
            mitre_tactics=["Credential Access"],
            mitre_techniques=["T1003"],
            tags=["credential-access"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_ssh_brute_force_signal",
            name="SSH Brute Force Signal",
            description="Linux authentication log indicates repeated SSH failures.",
            severity=EventSeverity.MEDIUM,
            source=EventSource.LINUX,
            event_type="auth_failure",
            conditions={
                "all": [
                    {
                        "field": "raw_event.message",
                        "operator": "contains",
                        "value": "Failed password",
                    }
                ],
            },
            mitre_tactics=["Credential Access"],
            mitre_techniques=["T1110"],
            tags=["ssh", "bruteforce"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_nmap_scan_detected",
            name="Nmap Scan Detected",
            description="Network telemetry contains Nmap scan indicators.",
            severity=EventSeverity.MEDIUM,
            source=EventSource.NETWORK,
            event_type="network_scan",
            conditions={
                "all": [
                    {"field": "raw_event.tool", "operator": "contains", "value": "nmap"}
                ],
            },
            mitre_tactics=["Reconnaissance"],
            mitre_techniques=["T1595"],
            tags=["scan"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_linux_cron_persistence",
            name="Linux Cron Persistence",
            description="Cron path modification can indicate persistence.",
            severity=EventSeverity.HIGH,
            source=EventSource.LINUX,
            event_type="file_write",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.file_path",
                        "operator": "contains",
                        "value": "/cron",
                    }
                ],
            },
            mitre_tactics=["Persistence"],
            mitre_techniques=["T1053.003"],
            tags=["persistence", "cron"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_reverse_shell_command",
            name="Reverse Shell Command",
            description="Command line contains common reverse shell patterns.",
            severity=EventSeverity.CRITICAL,
            source=EventSource.LINUX,
            event_type="process_start",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "regex",
                        "value": "bash -i|/dev/tcp|nc -e",
                    }
                ],
            },
            mitre_tactics=["Execution"],
            mitre_techniques=["T1059"],
            tags=["reverse-shell"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_suspicious_base64_command",
            name="Suspicious Base64 Command",
            description="Command line includes base64 decode execution patterns.",
            severity=EventSeverity.MEDIUM,
            source=EventSource.LINUX,
            event_type="process_start",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "contains",
                        "value": "base64",
                    },
                    {
                        "field": "normalized_fields.command_line",
                        "operator": "contains",
                        "value": "-d",
                    },
                ],
            },
            mitre_tactics=["Defense Evasion"],
            mitre_techniques=["T1027"],
            tags=["base64"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_large_outbound_transfer",
            name="Large Outbound Transfer",
            description="Large outbound byte count can indicate exfiltration.",
            severity=EventSeverity.HIGH,
            source=EventSource.NETWORK,
            event_type="network_connection",
            conditions={
                "all": [
                    {
                        "field": "normalized_fields.direction",
                        "operator": "equals",
                        "value": "outbound",
                    },
                    {
                        "field": "normalized_fields.bytes_sent",
                        "operator": "gte",
                        "value": 100000000,
                    },
                ],
            },
            mitre_tactics=["Exfiltration"],
            mitre_techniques=["T1041"],
            tags=["exfiltration"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_multiple_failed_windows_logons",
            name="Multiple Failed Windows Logons",
            description="Windows logon telemetry indicates repeated failures.",
            severity=EventSeverity.MEDIUM,
            source=EventSource.WINDOWS,
            event_type="logon_failure",
            conditions={
                "all": [
                    {"field": "normalized_fields.failure_count", "operator": "gte", "value": 5}
                ],
            },
            mitre_tactics=["Credential Access"],
            mitre_techniques=["T1110"],
            tags=["windows", "bruteforce"],
            created_at=now,
            updated_at=now,
        ),
        DetectionRule(
            id="builtin_vm_based_attacker_fingerprint",
            name="Possible VM-Based Attacker Fingerprint",
            description="Reconnaissance traffic includes common VM tooling fingerprints.",
            severity=EventSeverity.LOW,
            source=EventSource.NETWORK,
            event_type="network_scan",
            conditions={
                "all": [
                    {
                        "field": "raw_event.user_agent",
                        "operator": "regex",
                        "value": "kali|parrot|virtualbox|vmware",
                    }
                ],
            },
            mitre_tactics=["Reconnaissance"],
            mitre_techniques=["T1595"],
            tags=["fingerprint"],
            created_at=now,
            updated_at=now,
        ),
    ]


class DetectionRuleRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["detection_rules"]

    async def list_for_organization(self, organization_id: str) -> list[DetectionRule]:
        cursor = self.collection.find({"organization_id": organization_id}).sort("created_at", -1)
        custom_rules = [DetectionRule.model_validate(document) async for document in cursor]
        return [*builtin_detection_rules(), *custom_rules]

    async def list_enabled_for_organization(self, organization_id: str) -> list[DetectionRule]:
        return [rule for rule in await self.list_for_organization(organization_id) if rule.enabled]

    async def find_by_id_for_organization(
        self,
        *,
        rule_id: str,
        organization_id: str,
    ) -> DetectionRule | None:
        builtin = next((rule for rule in builtin_detection_rules() if rule.id == rule_id), None)
        if builtin is not None:
            return builtin
        document = await self.collection.find_one(
            {"id": rule_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return DetectionRule.model_validate(document)

    async def create(self, *, organization_id: str, rule: Any) -> DetectionRule:
        now = datetime.now(UTC)
        detection_rule = DetectionRule(
            id=f"rule_{uuid4().hex}",
            organization_id=organization_id,
            name=rule.name,
            description=rule.description,
            enabled=rule.enabled,
            severity=rule.severity,
            source=rule.source,
            event_type=rule.event_type,
            conditions=rule.conditions,
            mitre_tactics=rule.mitre_tactics,
            mitre_techniques=rule.mitre_techniques,
            tags=rule.tags,
            created_at=now,
            updated_at=now,
        )
        await self.collection.insert_one(detection_rule.model_dump(mode="json"))
        return detection_rule

    async def update(
        self,
        *,
        rule_id: str,
        organization_id: str,
        updates: dict[str, Any],
    ) -> DetectionRule | None:
        if not updates:
            return await self.find_by_id_for_organization(
                rule_id=rule_id,
                organization_id=organization_id,
            )
        updates["updated_at"] = datetime.now(UTC)
        document = await self.collection.find_one_and_update(
            {"id": rule_id, "organization_id": organization_id},
            {"$set": updates},
            return_document=ReturnDocument.AFTER,
        )
        if document is None:
            return None
        return DetectionRule.model_validate(document)

    async def set_enabled(
        self,
        *,
        rule_id: str,
        organization_id: str,
        enabled: bool,
    ) -> DetectionRule | None:
        return await self.update(
            rule_id=rule_id,
            organization_id=organization_id,
            updates={"enabled": enabled},
        )


class DetectionResultRepository:
    def __init__(self, database: AsyncIOMotorDatabase) -> None:
        self.collection = database["detection_results"]

    async def create(
        self,
        *,
        event: Event,
        rule: DetectionRule,
        matched_fields: dict[str, Any],
    ) -> DetectionResult:
        result = DetectionResult(
            id=f"det_{uuid4().hex}",
            organization_id=event.organization_id,
            agent_id=event.agent_id,
            event_id=event.id,
            rule_id=rule.id,
            rule_name=rule.name,
            severity=rule.severity,
            title=rule.name,
            description=rule.description,
            mitre_tactics=rule.mitre_tactics,
            mitre_techniques=rule.mitre_techniques,
            matched_fields=matched_fields,
            created_at=datetime.now(UTC),
        )
        await self.collection.insert_one(result.model_dump(mode="json"))
        return result

    async def list_by_organization(
        self,
        *,
        organization_id: str,
        limit: int = 100,
        skip: int = 0,
    ) -> list[DetectionResult]:
        cursor = (
            self.collection.find({"organization_id": organization_id})
            .sort("created_at", -1)
            .skip(skip)
            .limit(limit)
        )
        return [DetectionResult.model_validate(document) async for document in cursor]

    async def find_by_id_for_organization(
        self,
        *,
        result_id: str,
        organization_id: str,
    ) -> DetectionResult | None:
        document = await self.collection.find_one(
            {"id": result_id, "organization_id": organization_id},
        )
        if document is None:
            return None
        return DetectionResult.model_validate(document)
