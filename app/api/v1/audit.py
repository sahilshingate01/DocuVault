"""Audit Ledger API: Query immutable trail, verify cryptographic chain integrity, and test tamper detection."""
import io
import csv
import json
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
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
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    status_filter: Optional[str] = Query(None, description="Filter by status (e.g. SUCCESS, DENIED, ALERT)"),
    start_date: Optional[datetime] = Query(None, description="Filter logs starting from timestamp"),
    end_date: Optional[datetime] = Query(None, description="Filter logs ending at timestamp"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves the chronological audit ledger with multi-parameter cryptographic filtering."""
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action)
    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)
    if resource_id:
        query = query.filter(AuditLog.resource_id == resource_id)
    if actor_id:
        query = query.filter(AuditLog.user_id == actor_id)
    if status_filter:
        query = query.filter(AuditLog.status == status_filter)
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)

    # Scoped to user's organization if not admin
    if not current_user.is_admin:
        query = query.filter(
            (AuditLog.organization_id == current_user.organization_id) | (AuditLog.organization_id.is_(None))
        )

    logs = query.order_by(AuditLog.sequence_number.desc()).offset(offset).limit(limit).all()
    return logs


@router.get("/export")
def export_audit_ledger(
    export_format: str = Query("csv", description="Export format: 'csv' or 'json'"),
    limit: int = Query(1000, ge=1, le=5000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports a certified tamper-evident audit ledger pack for judicial or compliance auditing.
    Outputs either CSV or JSON with full SHA-256 hash chains.
    """
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_export):
        raise HTTPException(status_code=403, detail="Position lacks authority to export audit ledgers.")

    query = db.query(AuditLog)
    if not current_user.is_admin:
        query = query.filter(
            (AuditLog.organization_id == current_user.organization_id) | (AuditLog.organization_id.is_(None))
        )
    logs = query.order_by(AuditLog.sequence_number.asc()).limit(limit).all()

    if export_format.lower() == "json":
        data = [
            {
                "sequence_number": log.sequence_number,
                "timestamp": log.timestamp.isoformat(),
                "action": log.action,
                "resource_type": log.resource_type,
                "resource_id": log.resource_id,
                "user_id": log.user_id,
                "user_email": log.user_email,
                "status": log.status,
                "prev_hash": log.previous_hash,
                "entry_hash": log.entry_hash,
                "details": log.details
            }
            for log in logs
        ]
        return Response(
            content=json.dumps(data, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=docuvault_audit_ledger.json"}
        )

    # Default CSV export
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Sequence", "Timestamp", "Action", "ResourceType", "ResourceId",
        "UserId", "Status", "PreviousHash", "EntryHash", "Details"
    ])
    for log in logs:
        writer.writerow([
            log.sequence_number,
            log.timestamp.isoformat(),
            log.action,
            log.resource_type,
            log.resource_id,
            log.user_id,
            log.status,
            log.previous_hash,
            log.entry_hash,
            log.details_json
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=docuvault_audit_ledger.csv"}
    )


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
        AuditLog.user_id == user_id
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
