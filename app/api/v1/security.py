"""Security Authorization Engine and Policy Evaluation Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ClassificationLevel, ActionType, ResourceType
from app.models.user import User
from app.models.document import Document
from app.schemas.security import (
    AccessEvaluationRequest,
    AccessEvaluationResponse,
    UserPermissionMatrix,
)
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.security_monitor import SecurityMonitorService
from app.services.audit_service import AuditService
from app.models.audit_log import AuditLog
from app.models.temporary_clearance import TemporaryClearance

router = APIRouter(prefix="/security", tags=["Security & Authorization Engine"])


@router.get("/dashboard")
def get_security_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Security Operations Center (SOC) telemetry dashboard:
    Aggregates ledger integrity, clearance metrics, access denial trends, and alert telemetry.
    """
    from datetime import datetime, timezone, timedelta

    now = datetime.now(timezone.utc)
    since_24h = now - timedelta(hours=24)

    org_filter = [AuditLog.organization_id == current_user.organization_id] if not current_user.is_admin else []

    total_audit_events = db.query(AuditLog).filter(*org_filter).count()
    denials_24h = db.query(AuditLog).filter(
        AuditLog.action == ActionType.ACCESS_DENIED.value,
        AuditLog.timestamp >= since_24h,
        *org_filter
    ).count()

    downloads_24h = db.query(AuditLog).filter(
        AuditLog.action == ActionType.DOWNLOAD.value,
        AuditLog.timestamp >= since_24h,
        *org_filter
    ).count()

    active_temp_clearances = db.query(TemporaryClearance).filter(
        TemporaryClearance.is_revoked == False,
        TemporaryClearance.valid_until >= now
    ).count()

    # User clearance distribution
    user_query = db.query(User)
    if not current_user.is_admin:
        user_query = user_query.filter(User.organization_id == current_user.organization_id)
    users = user_query.all()
    user_clearance_dist = {}
    for u in users:
        eff = AccessControlService.get_effective_clearance(u).value
        user_clearance_dist[eff] = user_clearance_dist.get(eff, 0) + 1

    # Document classification distribution
    doc_query = db.query(Document)
    if not current_user.is_admin:
        doc_query = doc_query.filter(Document.workspace.has(organization_id=current_user.organization_id))
    docs = doc_query.all()
    doc_class_dist = {}
    for d in docs:
        doc_class_dist[d.classification] = doc_class_dist.get(d.classification, 0) + 1

    alerts = SecurityMonitorService.get_security_alerts(db, org_id=None if current_user.is_admin else current_user.organization_id)

    integrity_check = AuditService.verify_ledger_integrity(db)

    return {
        "ledger_integrity": {
            "is_valid": integrity_check["is_valid"],
            "total_blocks": integrity_check["total_entries"],
            "tampered_blocks": integrity_check["tampered_entries"]
        },
        "activity_metrics_24h": {
            "total_audit_events": total_audit_events,
            "access_denials": denials_24h,
            "downloads": downloads_24h
        },
        "active_temporary_clearances": active_temp_clearances,
        "security_posture": {
            "user_clearance_distribution": user_clearance_dist,
            "document_classification_distribution": doc_class_dist,
            "active_alerts_count": len(alerts),
            "critical_threats": sum(1 for a in alerts if a["severity"] == "CRITICAL")
        }
    }


@router.get("/alerts")
def get_security_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves real-time security anomalies, tamper events, and repeated clearance violations."""
    org_id = None if current_user.is_admin else current_user.organization_id
    alerts = SecurityMonitorService.get_security_alerts(db, org_id=org_id)
    return {
        "active_alerts_count": len(alerts),
        "critical_count": sum(1 for a in alerts if a["severity"] == "CRITICAL"),
        "high_count": sum(1 for a in alerts if a["severity"] == "HIGH"),
        "alerts": alerts
    }


@router.post("/evaluate", response_model=AccessEvaluationResponse)
def evaluate_access(
    data: AccessEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Real-time ABAC Permission Evaluation Engine:
    Evaluates multi-attribute policy parameters (Subject, Resource, Action, Environment)
    and returns an explicit ALLOW or DENY determination with an exhaustive rule trace.
    """
    user_to_evaluate = current_user
    if data.target_user_id and current_user.is_admin:
        simulated = db.query(User).filter(User.id == data.target_user_id).first()
        if simulated:
            user_to_evaluate = simulated

    result = AccessControlService.evaluate_abac_policy(
        db=db,
        user=user_to_evaluate,
        action=data.action.upper(),
        resource_type=data.resource_type.upper(),
        resource_id=data.resource_id
    )

    return AccessEvaluationResponse(**result)


@router.get("/permissions/my", response_model=UserPermissionMatrix)
def get_my_permission_matrix(
    current_user: User = Depends(get_current_user)
):
    """Returns the caller's effective access capability matrix and accessible classification tiers."""
    effective_clearance = AccessControlService.get_effective_clearance(current_user)
    permitted_classifications = [
        c.value for c in ClassificationLevel if ClassificationLevel.can_access(effective_clearance, c)
    ]

    return UserPermissionMatrix(
        user_id=current_user.id,
        email=current_user.email,
        clearance_level=current_user.clearance_level,
        effective_clearance=effective_clearance.value,
        is_admin=current_user.is_admin,
        position_title=current_user.position.title if current_user.position else None,
        designation_type=getattr(current_user.position, "designation_type", None) if current_user.position else None,
        can_sign=current_user.position.can_sign if current_user.position else False,
        can_approve=current_user.position.can_approve if current_user.position else False,
        can_export=current_user.position.can_export if current_user.position else False,
        can_manage_users=current_user.position.can_manage_users if current_user.position else False,
        allowed_actions=current_user.position.allowed_actions if current_user.position else ["READ"],
        permitted_classifications=permitted_classifications
    )


@router.get("/validate-document/{document_id}")
def validate_document_access(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pre-flight check returning all permitted operations for this user on a specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    actions = [
        ActionType.READ.value,
        ActionType.UPDATE.value,
        ActionType.DOWNLOAD.value,
        ActionType.APPROVE.value,
        ActionType.SIGN.value,
        ActionType.DELETE.value,
    ]

    operation_rights = {}
    for action in actions:
        res = AccessControlService.evaluate_abac_policy(
            db=db,
            user=current_user,
            action=action,
            resource_type=ResourceType.DOCUMENT.value,
            resource_id=doc.id
        )
        operation_rights[action] = res["allowed"]

    return {
        "document_id": doc.id,
        "document_number": doc.document_number,
        "classification": doc.classification,
        "operation_rights": operation_rights
    }
