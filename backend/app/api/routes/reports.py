from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from app.api.dependencies import get_audit_service, get_report_service, require_roles
from app.models.auth import Role
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.report_service import ReportFile, ReportService

router = APIRouter(prefix="/reports", tags=["reports"])

READ_REPORT_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST, Role.VIEWER)
ALL_REPORT_ROLES = (Role.SUPER_ADMIN, Role.ORG_ADMIN, Role.ANALYST)


@router.get("/incidents/{incident_id}.pdf")
async def export_incident_report(
    incident_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_REPORT_ROLES))],
    reports: Annotated[ReportService, Depends(get_report_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    report = await reports.incident_report(incident_id=incident_id, current_user=current_user)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    await audit.log(
        action="report.incident_export",
        resource_type="incident",
        resource_id=incident_id,
        description="Incident PDF report exported",
        request=request,
        current_user=current_user,
        metadata={"filename": report.filename},
    )
    return report_response(report)


@router.get("/attack-chains/{chain_id}.pdf")
async def export_attack_chain_report(
    chain_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_REPORT_ROLES))],
    reports: Annotated[ReportService, Depends(get_report_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    report = await reports.attack_chain_report(chain_id=chain_id, current_user=current_user)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Attack chain not found")
    await audit.log(
        action="report.attack_chain_export",
        resource_type="attack_chain",
        resource_id=chain_id,
        description="Attack chain PDF report exported",
        request=request,
        current_user=current_user,
        metadata={"filename": report.filename},
    )
    return report_response(report)


@router.get("/evidence/{evidence_id}.pdf")
async def export_evidence_report(
    evidence_id: str,
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_REPORT_ROLES))],
    reports: Annotated[ReportService, Depends(get_report_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    report = await reports.evidence_report(evidence_id=evidence_id, current_user=current_user)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evidence not found")
    await audit.log(
        action="report.evidence_export",
        resource_type="evidence",
        resource_id=evidence_id,
        description="Evidence PDF report exported",
        request=request,
        current_user=current_user,
        metadata={"filename": report.filename},
    )
    return report_response(report)


@router.get("/audit.csv")
async def export_audit_csv(
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*ALL_REPORT_ROLES))],
    reports: Annotated[ReportService, Depends(get_report_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    report = await reports.audit_csv(current_user=current_user)
    await audit.log(
        action="report.audit_export",
        resource_type="audit_log",
        description="Audit CSV report exported",
        request=request,
        current_user=current_user,
        metadata={"filename": report.filename},
    )
    return report_response(report)


@router.get("/executive-summary.pdf")
async def export_executive_summary(
    request: Request,
    current_user: Annotated[User, Depends(require_roles(*READ_REPORT_ROLES))],
    reports: Annotated[ReportService, Depends(get_report_service)],
    audit: Annotated[AuditService, Depends(get_audit_service)],
) -> Response:
    report = await reports.executive_summary(current_user=current_user)
    await audit.log(
        action="report.executive_summary_export",
        resource_type="executive_summary",
        description="Executive summary PDF report exported",
        request=request,
        current_user=current_user,
        metadata={"filename": report.filename},
    )
    return report_response(report)


def report_response(report: ReportFile) -> Response:
    return Response(
        content=report.content,
        media_type=report.media_type,
        headers={"Content-Disposition": f'attachment; filename="{report.filename}"'},
    )
