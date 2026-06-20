from __future__ import annotations

import csv
import io
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.alert import Alert
from app.models.attack_chain import AttackChain
from app.models.audit_log import AuditLog
from app.models.evidence import Evidence, EvidenceCustodyEvent
from app.models.incident import Incident
from app.models.organization import Organization
from app.models.user import User
from app.repositories.alerts import AlertRepository
from app.repositories.attack_chains import AttackChainRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.evidence import EvidenceCustodyRepository, EvidenceRepository
from app.repositories.incidents import IncidentRepository
from app.repositories.organizations import OrganizationRepository


@dataclass(frozen=True)
class ReportFile:
    content: bytes
    filename: str
    media_type: str


class ReportService:
    def __init__(
        self,
        *,
        organizations: OrganizationRepository,
        incidents: IncidentRepository,
        attack_chains: AttackChainRepository,
        evidence: EvidenceRepository,
        custody: EvidenceCustodyRepository,
        alerts: AlertRepository,
        audit_logs: AuditLogRepository,
    ) -> None:
        self._organizations = organizations
        self._incidents = incidents
        self._attack_chains = attack_chains
        self._evidence = evidence
        self._custody = custody
        self._alerts = alerts
        self._audit_logs = audit_logs
        self._styles = getSampleStyleSheet()
        self._styles.add(
            ParagraphStyle(
                name="SentinelSmall",
                parent=self._styles["BodyText"],
                fontSize=8,
                leading=10,
                textColor=colors.HexColor("#4b5563"),
            ),
        )
        self._styles.add(
            ParagraphStyle(
                name="SentinelHeading",
                parent=self._styles["Heading2"],
                textColor=colors.HexColor("#111827"),
                spaceAfter=8,
            ),
        )

    async def incident_report(self, *, incident_id: str, current_user: User) -> ReportFile | None:
        incident = await self._incidents.find_by_id_for_organization(
            incident_id=incident_id,
            organization_id=current_user.organization_id,
        )
        if incident is None:
            return None

        organization = await self._organization(current_user.organization_id)
        alerts = await self._alerts.find_many_by_ids_for_organization(
            alert_ids=incident.alert_ids,
            organization_id=current_user.organization_id,
        )
        linked_evidence = await self._evidence.list_by_organization(
            organization_id=current_user.organization_id,
            incident_id=incident.id,
            limit=500,
        )
        chain = await self._attack_chains.find_by_incident_for_organization(
            incident_id=incident.id,
            organization_id=current_user.organization_id,
        )
        audit_refs = await self._audit_logs.list_for_resource(
            organization_id=current_user.organization_id,
            resource_type="incident",
            resource_id=incident.id,
            limit=100,
        )

        story = [
            self._heading("Incident Details"),
            self._kv_table(
                [
                    ("Incident ID", incident.id),
                    ("Title", incident.title),
                    ("Severity", incident.severity.value),
                    ("Status", incident.status.value),
                    ("First Seen", self._format_dt(incident.first_seen_at)),
                    ("Last Seen", self._format_dt(incident.last_seen_at)),
                    ("Assigned User", incident.assigned_to_user_id or "Unassigned"),
                    ("Description", incident.description),
                    ("Summary", incident.summary or "No analyst summary recorded."),
                ]
            ),
            self._heading("MITRE Techniques"),
            self._bullet_list(incident.mitre_techniques or ["No techniques recorded."]),
            self._heading("Alerts"),
            self._alerts_table(alerts, incident.alert_ids),
            self._heading("Evidence Hashes"),
            self._evidence_table(linked_evidence),
            self._heading("Chain of Custody Events"),
            *await self._custody_sections(linked_evidence),
            self._heading("Audit References"),
            self._audit_table(audit_refs),
            self._heading("Recommended Actions"),
            self._bullet_list(self._incident_actions(incident, chain)),
        ]
        content = self._pdf(
            title=f"Incident Report: {incident.title}",
            organization=organization,
            current_user=current_user,
            body=story,
        )
        return ReportFile(
            content=content,
            filename=f"sentinelxdr-incident-{incident.id}.pdf",
            media_type="application/pdf",
        )

    async def attack_chain_report(self, *, chain_id: str, current_user: User) -> ReportFile | None:
        chain = await self._attack_chains.find_by_id_for_organization(
            chain_id=chain_id,
            organization_id=current_user.organization_id,
        )
        if chain is None:
            return None

        organization = await self._organization(current_user.organization_id)
        alerts = await self._alerts.find_many_by_ids_for_organization(
            alert_ids=chain.alert_ids,
            organization_id=current_user.organization_id,
        )
        linked_evidence = await self._evidence.list_by_organization(
            organization_id=current_user.organization_id,
            incident_id=chain.incident_id,
            limit=500,
        )
        audit_refs = await self._audit_logs.list_for_resource(
            organization_id=current_user.organization_id,
            resource_type="attack_chain",
            resource_id=chain.id,
            limit=100,
        )

        body = [
            self._heading("Attack Chain Details"),
            self._kv_table(
                [
                    ("Chain ID", chain.id),
                    ("Incident ID", chain.incident_id),
                    ("Title", chain.title),
                    ("Severity", chain.severity.value),
                    ("Status", chain.status.value),
                    ("Risk Score", f"{chain.risk_score:.2f}"),
                    ("Confidence Score", f"{chain.confidence_score:.2f}"),
                    ("First Seen", self._format_dt(chain.first_seen_at)),
                    ("Last Seen", self._format_dt(chain.last_seen_at)),
                    ("Summary", chain.summary),
                    ("Threat Story", chain.story),
                ]
            ),
            self._heading("Kill Chain Phases"),
            self._bullet_list(chain.kill_chain_phases or ["No phases recorded."]),
            self._heading("MITRE Techniques"),
            self._bullet_list(chain.mitre_techniques or ["No techniques recorded."]),
            self._heading("Timeline"),
            self._timeline_table(chain),
            self._heading("Alerts"),
            self._alerts_table(alerts, chain.alert_ids),
            self._heading("Evidence Hashes"),
            self._evidence_table(linked_evidence),
            self._heading("Chain of Custody Events"),
            *await self._custody_sections(linked_evidence),
            self._heading("Audit References"),
            self._audit_table(audit_refs),
            self._heading("Recommended Actions"),
            self._bullet_list(chain.recommended_actions or ["Review linked incident and alerts."]),
        ]
        content = self._pdf(
            title=f"Attack Chain Report: {chain.title}",
            organization=organization,
            current_user=current_user,
            body=body,
        )
        return ReportFile(
            content=content,
            filename=f"sentinelxdr-attack-chain-{chain.id}.pdf",
            media_type="application/pdf",
        )

    async def evidence_report(self, *, evidence_id: str, current_user: User) -> ReportFile | None:
        evidence = await self._evidence.find_by_id_for_organization(
            evidence_id=evidence_id,
            organization_id=current_user.organization_id,
        )
        if evidence is None:
            return None

        organization = await self._organization(current_user.organization_id)
        incident = None
        if evidence.incident_id is not None:
            incident = await self._incidents.find_by_id_for_organization(
                incident_id=evidence.incident_id,
                organization_id=current_user.organization_id,
            )
        custody_events = await self._custody.list_for_evidence(
            organization_id=current_user.organization_id,
            evidence_id=evidence.id,
            limit=500,
        )
        audit_refs = await self._audit_logs.list_for_resource(
            organization_id=current_user.organization_id,
            resource_type="evidence",
            resource_id=evidence.id,
            limit=100,
        )

        body = [
            self._heading("Evidence Details"),
            self._kv_table(
                [
                    ("Evidence ID", evidence.id),
                    ("Original Filename", evidence.original_filename),
                    ("Stored Filename", evidence.filename),
                    ("Content Type", evidence.content_type),
                    ("Size Bytes", str(evidence.size_bytes)),
                    ("SHA-256", evidence.sha256),
                    ("Status", evidence.status.value),
                    ("Verification", evidence.verification_status.value),
                    ("Last Verified", self._format_dt(evidence.last_verified_at)),
                    ("Uploaded By", evidence.uploaded_by_email),
                    ("Uploaded At", self._format_dt(evidence.created_at)),
                    ("Description", evidence.description or "No description recorded."),
                    ("Tags", ", ".join(evidence.tags) or "None"),
                ]
            ),
            self._heading("Linked Incident"),
            self._incident_summary(incident),
            self._heading("Chain of Custody Events"),
            self._custody_table(custody_events),
            self._heading("Audit References"),
            self._audit_table(audit_refs),
            self._heading("Recommended Actions"),
            self._bullet_list(self._evidence_actions(evidence, custody_events)),
        ]
        content = self._pdf(
            title=f"Evidence Report: {evidence.original_filename}",
            organization=organization,
            current_user=current_user,
            body=body,
        )
        return ReportFile(
            content=content,
            filename=f"sentinelxdr-evidence-{evidence.id}.pdf",
            media_type="application/pdf",
        )

    async def audit_csv(self, *, current_user: User) -> ReportFile:
        logs = await self._audit_logs.list_for_organization(
            organization_id=current_user.organization_id,
            limit=5000,
        )
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "id",
                "organization_id",
                "created_at",
                "actor_email",
                "actor_role",
                "action",
                "resource_type",
                "resource_id",
                "status",
                "ip_address",
                "description",
            ]
        )
        for log in logs:
            writer.writerow(
                [
                    log.id,
                    log.organization_id or "",
                    self._format_dt(log.created_at),
                    log.actor_email or "",
                    log.actor_role or "",
                    log.action,
                    log.resource_type,
                    log.resource_id or "",
                    log.status.value,
                    log.ip_address or "",
                    log.description,
                ]
            )
        return ReportFile(
            content=output.getvalue().encode("utf-8"),
            filename="sentinelxdr-audit.csv",
            media_type="text/csv; charset=utf-8",
        )

    async def executive_summary(self, *, current_user: User) -> ReportFile:
        organization = await self._organization(current_user.organization_id)
        incidents = await self._incidents.list_by_organization(
            organization_id=current_user.organization_id,
            limit=500,
        )
        chains = await self._attack_chains.list_by_organization(
            organization_id=current_user.organization_id,
            limit=500,
        )
        evidence = await self._evidence.list_by_organization(
            organization_id=current_user.organization_id,
            limit=500,
        )
        alerts = await self._alerts.list_by_organization(
            organization_id=current_user.organization_id,
            limit=500,
        )

        open_incidents = [
            item for item in incidents if item.status.value in {"open", "investigating"}
        ]
        active_chains = [item for item in chains if item.status.value == "active"]
        techniques = Counter(
            technique
            for source in [*alerts, *incidents, *chains]
            for technique in source.mitre_techniques
        )
        actions = self._executive_actions(open_incidents, active_chains, evidence)

        body = [
            self._heading("Executive Overview"),
            self._kv_table(
                [
                    ("Total Incidents", str(len(incidents))),
                    ("Open / Investigating Incidents", str(len(open_incidents))),
                    ("Total Attack Chains", str(len(chains))),
                    ("Active Attack Chains", str(len(active_chains))),
                    ("Total Alerts", str(len(alerts))),
                    ("Evidence Items", str(len(evidence))),
                ]
            ),
            self._heading("Top MITRE Techniques"),
            self._simple_table(
                ["Technique", "Occurrences"],
                [(technique, str(count)) for technique, count in techniques.most_common(10)]
                or [("None recorded", "0")],
            ),
            self._heading("Highest Risk Attack Chains"),
            self._simple_table(
                ["Chain", "Severity", "Risk", "Status"],
                [
                    (
                        chain.title,
                        chain.severity.value,
                        f"{chain.risk_score:.2f}",
                        chain.status.value,
                    )
                    for chain in sorted(chains, key=lambda item: item.risk_score, reverse=True)[:10]
                ]
                or [("None recorded", "", "", "")],
            ),
            self._heading("Recent Incidents"),
            self._simple_table(
                ["Incident", "Severity", "Status", "Last Seen"],
                [
                    (
                        incident.title,
                        incident.severity.value,
                        incident.status.value,
                        self._format_dt(incident.last_seen_at),
                    )
                    for incident in incidents[:10]
                ]
                or [("None recorded", "", "", "")],
            ),
            self._heading("Recommended Actions"),
            self._bullet_list(actions),
        ]
        content = self._pdf(
            title="Executive Security Summary",
            organization=organization,
            current_user=current_user,
            body=body,
        )
        return ReportFile(
            content=content,
            filename="sentinelxdr-executive-summary.pdf",
            media_type="application/pdf",
        )

    async def _organization(self, organization_id: str) -> Organization:
        organization = await self._organizations.find_by_id(organization_id)
        if organization is not None:
            return organization
        return Organization(id=organization_id, name=organization_id)

    def _pdf(
        self,
        *,
        title: str,
        organization: Organization,
        current_user: User,
        body: list[Any],
    ) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=LETTER,
            rightMargin=0.55 * inch,
            leftMargin=0.55 * inch,
            topMargin=0.6 * inch,
            bottomMargin=0.55 * inch,
        )
        generated_at = datetime.now(UTC)
        story: list[Any] = [
            Paragraph(self._text(title), self._styles["Title"]),
            Spacer(1, 8),
            self._kv_table(
                [
                    ("Organization", organization.name),
                    ("Generated By", f"{current_user.display_name} <{current_user.email}>"),
                    ("Generated At", self._format_dt(generated_at)),
                ]
            ),
            Spacer(1, 12),
            *body,
        ]
        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        return buffer.getvalue()

    def _footer(self, canvas: Any, doc: SimpleDocTemplate) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6b7280"))
        canvas.drawString(0.55 * inch, 0.32 * inch, "SentinelAI XDR Report Export")
        canvas.drawRightString(7.95 * inch, 0.32 * inch, f"Page {doc.page}")
        canvas.restoreState()

    def _heading(self, text: str) -> Any:
        return Paragraph(self._text(text), self._styles["SentinelHeading"])

    def _kv_table(self, rows: list[tuple[str, str]]) -> Table:
        return self._simple_table(["Field", "Value"], rows, widths=[1.7 * inch, 5.25 * inch])

    def _simple_table(
        self,
        headers: list[str],
        rows: list[tuple[Any, ...]],
        widths: list[float] | None = None,
    ) -> Table:
        if widths is None:
            widths = [6.95 * inch / len(headers)] * len(headers)
        table_rows = [
            [
                Paragraph(self._cell_text(header), self._styles["SentinelSmall"])
                for header in headers
            ],
        ]
        for row in rows:
            table_rows.append(
                [Paragraph(self._cell_text(str(cell)), self._styles["BodyText"]) for cell in row]
            )
        table = Table(table_rows, colWidths=widths, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f3f4f6")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#111827")),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d1d5db")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def _bullet_list(self, values: list[str]) -> ListFlowable:
        return ListFlowable(
            [ListItem(Paragraph(self._text(value), self._styles["BodyText"])) for value in values],
            bulletType="bullet",
            start="circle",
            leftIndent=18,
        )

    def _alerts_table(self, alerts: list[Alert], fallback_ids: list[str]) -> Table:
        if alerts:
            rows = [
                (alert.id, alert.title, alert.severity.value, alert.status.value)
                for alert in alerts
            ]
        else:
            rows = [(alert_id, "Metadata unavailable", "", "") for alert_id in fallback_ids]
        return self._simple_table(["Alert ID", "Title", "Severity", "Status"], rows)

    def _evidence_table(self, evidence: list[Evidence]) -> Table:
        rows = [
            (
                item.id,
                item.original_filename,
                item.sha256,
                item.verification_status.value,
            )
            for item in evidence
        ] or [("None linked", "", "", "")]
        return self._simple_table(["Evidence ID", "Filename", "SHA-256", "Verification"], rows)

    async def _custody_sections(self, evidence: list[Evidence]) -> list[Any]:
        if not evidence:
            return [Paragraph("No evidence custody events recorded.", self._styles["BodyText"])]
        sections: list[Any] = []
        for item in evidence[:20]:
            sections.append(Paragraph(self._text(item.original_filename), self._styles["Heading4"]))
            events = await self._custody.list_for_evidence(
                organization_id=item.organization_id,
                evidence_id=item.id,
                limit=100,
            )
            sections.append(self._custody_table(events))
        return sections

    def _custody_table(self, events: list[EvidenceCustodyEvent]) -> Table:
        rows = [
            (
                self._format_dt(event.created_at),
                event.action.value,
                event.actor_email or "System",
                event.description,
            )
            for event in events
        ] or [("None recorded", "", "", "")]
        return self._simple_table(["Timestamp", "Action", "Actor", "Description"], rows)

    def _audit_table(self, logs: list[AuditLog]) -> Table:
        rows = [
            (
                self._format_dt(log.created_at),
                log.action,
                log.actor_email or "System",
                log.status.value,
            )
            for log in logs
        ] or [("No audit references found", "", "", "")]
        return self._simple_table(["Timestamp", "Action", "Actor", "Status"], rows)

    def _timeline_table(self, chain: AttackChain) -> Table:
        rows = [
            (
                self._format_dt(node.timestamp),
                node.type.value,
                node.title,
                node.mitre_technique or "",
                node.reference_id,
            )
            for node in chain.timeline[:40]
        ] or [("No timeline events recorded", "", "", "", "")]
        return self._simple_table(["Timestamp", "Type", "Title", "MITRE", "Reference"], rows)

    def _incident_summary(self, incident: Incident | None) -> Any:
        if incident is None:
            return Paragraph("No linked incident metadata available.", self._styles["BodyText"])
        return self._kv_table(
            [
                ("Incident ID", incident.id),
                ("Title", incident.title),
                ("Severity", incident.severity.value),
                ("Status", incident.status.value),
                ("Summary", incident.summary or incident.description),
            ]
        )

    def _incident_actions(self, incident: Incident, chain: AttackChain | None) -> list[str]:
        if chain is not None and chain.recommended_actions:
            return chain.recommended_actions
        if incident.severity.value in {"critical", "high"}:
            return [
                "Assign an analyst and begin containment review.",
                "Validate linked alerts and affected agents.",
                "Collect or verify evidence for affected systems.",
            ]
        if incident.status.value in {"open", "investigating"}:
            return ["Continue triage and document analyst summary."]
        return ["Review closure notes and retain evidence according to policy."]

    def _evidence_actions(
        self,
        evidence: Evidence,
        custody_events: list[EvidenceCustodyEvent],
    ) -> list[str]:
        actions: list[str] = []
        if evidence.verification_status.value != "verified":
            actions.append("Run evidence hash verification before legal or executive review.")
        if not custody_events:
            actions.append("Record chain-of-custody events for this evidence item.")
        if evidence.incident_id is None:
            actions.append("Link the evidence item to an incident if it supports an investigation.")
        return actions or ["Maintain custody history and preserve the original artifact."]

    def _executive_actions(
        self,
        open_incidents: list[Incident],
        active_chains: list[AttackChain],
        evidence: list[Evidence],
    ) -> list[str]:
        actions: list[str] = []
        if active_chains:
            actions.append("Prioritize containment for active attack chains.")
        if open_incidents:
            actions.append("Ensure every open or investigating incident has an owner.")
        if any(item.verification_status.value != "verified" for item in evidence):
            actions.append("Verify outstanding evidence hashes for active investigations.")
        return actions or ["Maintain monitoring and continue routine review cadence."]

    def _format_dt(self, value: datetime | None) -> str:
        if value is None:
            return "Not recorded"
        return value.astimezone(UTC).isoformat()

    def _text(self, value: str) -> str:
        return escape(value)

    def _cell_text(self, value: str) -> str:
        words = value.split(" ")
        wrapped_words = [
            "<br/>".join(word[index : index + 32] for index in range(0, len(word), 32))
            if len(word) > 32
            else word
            for word in words
        ]
        return escape(" ".join(wrapped_words)).replace("&lt;br/&gt;", "<br/>")
