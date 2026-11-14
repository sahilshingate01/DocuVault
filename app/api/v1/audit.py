"""Audit Ledger API: Query immutable trail, verify cryptographic chain integrity, and test tamper detection."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.audit_log import AuditLog
from app.schemas.audit import AuditLogResponse, AuditIntegrityResponse
from app.api.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit", tags=["Audit Ledger"])


@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(
    action: Optional[str] = Query(None, description="Filter by action (e.g. READ, WRITE, SIGN, ACCESS_DENIED)"),
    resource_type: Optional[str] = Query(None, description="Filter by resource (e.g. DOCUMENT, WORKSPACE)"),
    resource_id: Optional[str] = Query(None, description="Filter by specific resource ID"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves the chronological audit ledger."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)

    # Scoped to user's organization if not admin
    if not current_user.is_admin:
        query = query.filter(
            (AuditLog.organization_id == current_user.organization_id) | (AuditLog.organization_id.is_(None))
        )

    logs = query.order_by(AuditLog.sequence_number.desc()).limit(limit).all()
    return logs


@router.get("/documents/{document_id}", response_model=List[AuditLogResponse])
def get_document_audit_trail(
    document_id: str,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exhaustive Provenance Trail:
    Retrieves all chronological records of uploads, reads, updates, downloads,
    approvals, signatures, classification changes, and verification checks for a specific document.
    """
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    version_ids = [v.id for v in doc.versions]
    target_resource_ids = [document_id] + version_ids

    logs = db.query(AuditLog).filter(
        (AuditLog.resource_id.in_(target_resource_ids)) |
        (AuditLog.details_json.contains(document_id)) |
        (AuditLog.details_json.contains(doc.document_number))
    ).order_by(AuditLog.sequence_number.asc()).limit(limit).all()

    return logs


@router.get("/actors/{user_id}", response_model=List[AuditLogResponse])
def get_actor_audit_trail(
    user_id: str,
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves all chronological activities executed by a specific user across the system."""
    if not current_user.is_admin and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Permission denied to inspect external user activity.")

    logs = db.query(AuditLog).filter(
        AuditLog.actor_id == user_id
    ).order_by(AuditLog.sequence_number.desc()).limit(limit).all()

    return logs


@router.get("/verify", response_model=AuditIntegrityResponse)
def verify_audit_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Cryptographic verification endpoint:
    Scans the entire ledger from Genesis block to head, re-calculating SHA-256 digests
    to confirm mathematical continuity and lack of data tampering.
    """
    result = AuditService.verify_ledger_integrity(db)
    return AuditIntegrityResponse(**result)


@router.post("/simulate-tampering", response_model=AuditIntegrityResponse)
def simulate_ledger_tampering(
    sequence_number: Optional[int] = Query(None, description="Sequence number to tamper with"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Demonstration tool: Deliberately mutates a database log row without updating its hash,
    proving that any direct SQL / database administrator tampering is mathematically caught!
    """
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_approve):
        raise HTTPException(status_code=403, detail="Only administrators or executive officers may run integrity simulation tests.")

    if sequence_number:
        target = db.query(AuditLog).filter(AuditLog.sequence_number == sequence_number).first()
    else:
        target = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).first()

    if not target:
        raise HTTPException(status_code=404, detail="No audit log entries found to simulate tampering on.")

    # Mutate the payload without recalculating entry_hash
    target.details_json = '{"tampered_by_malicious_actor": true, "original_content_altered": "CRIMINAL_STATEMENT_REMOVED"}'
    db.commit()

    # Re-run verification to highlight the tamper detection
    result = AuditService.verify_ledger_integrity(db)
    return AuditIntegrityResponse(**result)


@router.post("/recalculate-ledger", response_model=AuditIntegrityResponse)
def recalculate_ledger(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restores the hash chain following an authorized integrity audit."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator privileges required.")

    logs = db.query(AuditLog).order_by(AuditLog.sequence_number.asc()).all()
    prev_hash = "0" * 64
    for log in logs:
        ts_str = log.timestamp_iso if getattr(log, "timestamp_iso", None) else log.timestamp.isoformat()
        log.previous_hash = prev_hash
        log.entry_hash = AuditService.compute_entry_hash(
            sequence_number=log.sequence_number,
            timestamp_iso=ts_str,
            previous_hash=prev_hash,
            user_id=log.user_id,
            action=log.action,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            status=log.status,
            details_json=log.details_json
        )
        prev_hash = log.entry_hash
    db.commit()

    result = AuditService.verify_ledger_integrity(db)
    return AuditIntegrityResponse(**result)
