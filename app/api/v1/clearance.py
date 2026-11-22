"""Temporary Clearance Delegation Endpoints."""
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel
from app.models.user import User
from app.models.temporary_clearance import TemporaryClearance
from app.schemas.clearance import TemporaryClearanceCreate, TemporaryClearanceResponse
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/clearance", tags=["Security Clearance Delegation"])


@router.post("/grant", response_model=TemporaryClearanceResponse, status_code=status.HTTP_201_CREATED)
def grant_temporary_clearance(
    data: TemporaryClearanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Grants time-bound elevated security clearance to a user for a specific workspace or document.
    Grantor must possess clearance equal to or greater than the level being granted.
    """
    grantor_clearance = AccessControlService.get_effective_clearance(current_user)
    if not ClassificationLevel.can_access(grantor_clearance, data.granted_clearance) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot grant clearance '{data.granted_clearance}': your clearance is '{grantor_clearance.value}'."
        )

    target_user = db.query(User).filter(User.id == data.user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found.")

    now = datetime.now(timezone.utc)
    valid_until = now + timedelta(hours=data.valid_hours)

    clearance_grant = TemporaryClearance(
        user_id=target_user.id,
        granted_by_id=current_user.id,
        granted_clearance=data.granted_clearance.upper(),
        workspace_id=data.workspace_id,
        document_id=data.document_id,
        reason=data.reason,
        valid_from=now,
        valid_until=valid_until,
        is_revoked=False
    )
    db.add(clearance_grant)
    db.commit()
    db.refresh(clearance_grant)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type="CLEARANCE_GRANT",
        resource_id=clearance_grant.id,
        actor=current_user,
        details={
            "action": "TEMPORARY_CLEARANCE_GRANTED",
            "target_user": target_user.email,
            "granted_clearance": clearance_grant.granted_clearance,
            "valid_until": valid_until.isoformat(),
            "reason": data.reason,
            "workspace_id": data.workspace_id,
            "document_id": data.document_id
        }
    )

    return clearance_grant


@router.get("/active", response_model=List[TemporaryClearanceResponse])
def list_active_clearances(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists currently active, non-revoked temporary clearance delegations."""
    now = datetime.now(timezone.utc)
    query = db.query(TemporaryClearance).filter(
        TemporaryClearance.is_revoked == False,
        TemporaryClearance.valid_until >= now
    )
    if user_id:
        query = query.filter(TemporaryClearance.user_id == user_id)
    elif not current_user.is_admin:
        query = query.filter(TemporaryClearance.user_id == current_user.id)

    return query.order_by(TemporaryClearance.valid_until.asc()).all()


@router.post("/{grant_id}/revoke", response_model=TemporaryClearanceResponse)
def revoke_temporary_clearance(
    grant_id: str,
    reason: str = Query("Administrative revocation", description="Revocation justification"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Immediately revokes an active temporary clearance delegation before its expiration date."""
    grant = db.query(TemporaryClearance).filter(TemporaryClearance.id == grant_id).first()
    if not grant:
        raise HTTPException(status_code=404, detail="Clearance grant not found.")

    if not current_user.is_admin and grant.granted_by_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the grantor or an administrator can revoke this clearance.")

    now = datetime.now(timezone.utc)
    grant.is_revoked = True
    grant.revoked_at = now
    grant.revocation_reason = reason
    db.commit()
    db.refresh(grant)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type="CLEARANCE_GRANT",
        resource_id=grant.id,
        actor=current_user,
        details={
            "action": "TEMPORARY_CLEARANCE_REVOKED",
            "grant_id": grant.id,
            "revocation_reason": reason
        }
    )

    return grant

