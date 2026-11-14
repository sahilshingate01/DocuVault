"""Document lifecycle endpoints: Secure upload, SHA-256 fingerprinting, versioning, and download."""
import os
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel, DocumentStatus
from app.models.user import User
from app.models.workspace import Workspace
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.schemas.document import (
    DocumentResponse,
    DocumentDetail,
    DocumentVersionResponse,
    DocumentUpdate,
    DocumentReclassifyRequest,
    DocumentArchiveRequest,
)
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.crypto_service import CryptoService
from app.services.storage_service import StorageService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/documents", tags=["Documents"])


def _to_doc_response(doc: Document) -> DocumentResponse:
    res = DocumentResponse.model_validate(doc)
    if doc.versions:
        latest = doc.versions[0]  # ordered by version_number desc
        res.current_version = DocumentVersionResponse.model_validate(latest)
    return res


@router.get("/trash/list", response_model=List[DocumentResponse])
def list_deleted_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists soft-deleted documents residing in the vault trash bin."""
    query = db.query(Document).filter(
        Document.is_deleted == True,
        Document.workspace.has(organization_id=current_user.organization_id)
    )
    docs = query.order_by(Document.deleted_at.desc()).all()
    return [_to_doc_response(d) for d in docs]


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    document_number: str = Form(...),
    workspace_id: str = Form(...),
    classification: str = Form("UNCLASSIFIED"),
    description: Optional[str] = Form(None),
    tags_json: Optional[str] = Form("[]"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Secure Document Upload:
    1. Validates workspace exists and user has WRITE authority.
    2. Enforces security classification clearance.
    3. Streams file into vault storage.
    4. Computes immutable SHA-256 fingerprint.
    5. Creates Document and Version 1 records.
    6. Appends tamper-evident audit record.
    """
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    # Access control on workspace
    AccessControlService.authorize_workspace(db, current_user, workspace, ActionType.WRITE.value)

    # Check classification clearance
    effective_clearance = AccessControlService.get_effective_clearance(current_user)
    if not ClassificationLevel.can_access(effective_clearance, classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot upload document classified '{classification}' with clearance '{effective_clearance.value}'."
        )

    # Duplicate document number check
    if db.query(Document).filter(Document.document_number == document_number).first():
        raise HTTPException(status_code=400, detail=f"Document number '{document_number}' already exists.")

    # Save file and calculate SHA-256 fingerprint
    file_path, sha256_hash, file_size = StorageService.save_upload_file(file)

    try:
        tags = json.loads(tags_json or "[]")
    except Exception:
        tags = []

    # Create Document entity
    document = Document(
        title=title,
        document_number=document_number,
        description=description,
        classification=classification,
        status=DocumentStatus.DRAFT.value,
        workspace_id=workspace.id,
        created_by_id=current_user.id,
        tags=tags
    )
    db.add(document)
    db.flush()

    # Create Document Version 1
    version = DocumentVersion(
        version_number=1,
        file_path=file_path,
        original_filename=file.filename or "document.bin",
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        sha256_hash=sha256_hash,
        change_summary="Initial upload and SHA-256 fingerprint generation",
        document_id=document.id,
        uploaded_by_id=current_user.id
    )
    db.add(version)
    db.commit()
    db.refresh(document)

    # Audit log entry
    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "document_number": document.document_number,
            "version": 1,
            "sha256_fingerprint": sha256_hash,
            "classification": document.classification,
            "workspace_code": workspace.code
        }
    )

    return _to_doc_response(document)


@router.post("/{document_id}/versions", response_model=DocumentResponse)
def upload_new_version(
    document_id: str,
    file: UploadFile = File(...),
    change_summary: Optional[str] = Form("Updated version"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new immutable version of an existing document with fresh SHA-256 fingerprint."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.UPDATE.value)

    # Calculate next version number
    next_ver = (document.versions[0].version_number + 1) if document.versions else 1

    file_path, sha256_hash, file_size = StorageService.save_upload_file(file)

    version = DocumentVersion(
        version_number=next_ver,
        file_path=file_path,
        original_filename=file.filename or "updated.bin",
        file_size=file_size,
        mime_type=file.content_type or "application/octet-stream",
        sha256_hash=sha256_hash,
        change_summary=change_summary,
        document_id=document.id,
        uploaded_by_id=current_user.id
    )
    db.add(version)
    # Reset status to DRAFT or PENDING_APPROVAL upon new version
    document.status = DocumentStatus.PENDING_APPROVAL.value
    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "document_number": document.document_number,
            "new_version": next_ver,
            "sha256_fingerprint": sha256_hash
        }
    )

    return _to_doc_response(document)


@router.get("/{document_id}/versions", response_model=List[DocumentVersionResponse])
def get_version_history(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves full version history of a document with cryptographic SHA-256 digests and approvals."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id
    ).order_by(DocumentVersion.version_number.desc()).all()

    return [DocumentVersionResponse.model_validate(v) for v in versions]


@router.post("/{document_id}/versions/{version_number}/restore", response_model=DocumentResponse)
def restore_version(
    document_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Rolls back / restores an earlier version as a new sequential version.
    Preserves audit history and cryptographic fingerprints without rewriting historical versions.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.UPDATE.value)

    target_version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id,
        DocumentVersion.version_number == version_number
    ).first()
    if not target_version:
        raise HTTPException(status_code=404, detail=f"Version {version_number} not found.")

    latest_ver = (document.versions[0].version_number + 1) if document.versions else 1

    new_version = DocumentVersion(
        version_number=latest_ver,
        file_path=target_version.file_path,
        original_filename=target_version.original_filename,
        file_size=target_version.file_size,
        mime_type=target_version.mime_type,
        sha256_hash=target_version.sha256_hash,
        change_summary=f"Rollback: Restored state of version {version_number}",
        document_id=document.id,
        uploaded_by_id=current_user.id
    )
    db.add(new_version)
    document.status = DocumentStatus.PENDING_APPROVAL.value
    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "action": "VERSION_ROLLBACK",
            "restored_from_version": version_number,
            "new_version": latest_ver,
            "sha256": target_version.sha256_hash
        }
    )

    return _to_doc_response(document)


@router.get("/{document_id}/versions/{version_number}/verify")
def verify_document_integrity(
    document_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Recalculate a stored version's SHA-256 fingerprint and compare it with its record."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id,
        DocumentVersion.version_number == version_number
    ).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")

    if not os.path.isfile(version.file_path):
        raise HTTPException(status_code=404, detail="Stored document file is missing.")

    with open(version.file_path, "rb") as stored_file:
        calculated_hash = CryptoService.calculate_sha256_stream(stored_file)

    is_intact = calculated_hash == version.sha256_hash
    AuditService.record(
        db=db,
        action=(ActionType.VERIFY_INTEGRITY.value if is_intact else ActionType.TAMPER_DETECTED.value),
        resource_type=ResourceType.DOCUMENT_VERSION.value,
        resource_id=version.id,
        actor=current_user,
        status=("SUCCESS" if is_intact else "ALERT"),
        details={
            "version_number": version.version_number,
            "stored_fingerprint": version.sha256_hash,
            "calculated_fingerprint": calculated_hash,
            "integrity_verified": is_intact
        }
    )

    return {
        "document_id": document.id,
        "version_number": version.version_number,
        "is_intact": is_intact,
        "stored_sha256": version.sha256_hash,
        "calculated_sha256": calculated_hash,
        "message": (
            "Document integrity verified. The stored file matches its original fingerprint."
            if is_intact else
            "Integrity check failed. The stored file may have been modified or corrupted."
        )
    }


@router.get("/{document_id}/verify")
def verify_all_document_versions_integrity(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Performs full forensic file verification on disk for ALL versions of a document.
    Returns status manifest confirming tamper-free state across complete document lifecycle.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    versions = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id
    ).order_by(DocumentVersion.version_number.asc()).all()

    version_results = []
    all_intact = True

    for v in versions:
        if not os.path.isfile(v.file_path):
            is_intact = False
            calculated_hash = None
        else:
            with open(v.file_path, "rb") as f:
                calculated_hash = CryptoService.calculate_sha256_stream(f)
            is_intact = (calculated_hash == v.sha256_hash)

        if not is_intact:
            all_intact = False

        version_results.append({
            "version_number": v.version_number,
            "is_intact": is_intact,
            "stored_sha256": v.sha256_hash,
            "calculated_sha256": calculated_hash
        })

    AuditService.record(
        db=db,
        action=(ActionType.VERIFY_INTEGRITY.value if all_intact else ActionType.TAMPER_DETECTED.value),
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        status=("SUCCESS" if all_intact else "ALERT"),
        details={
            "document_number": document.document_number,
            "all_versions_intact": all_intact,
            "verified_versions_count": len(version_results)
        }
    )

    return {
        "document_id": document.id,
        "document_number": document.document_number,
        "all_versions_intact": all_intact,
        "total_versions": len(version_results),
        "versions": version_results,
        "status": "SECURE_AND_VERIFIED" if all_intact else "INTEGRITY_COMPROMISED"
    }


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document_metadata(
    document_id: str,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates document metadata such as title, description, and searchable tags."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.UPDATE.value)

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(document, key, value)

    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={"updated_fields": list(update_dict.keys()), "document_number": document.document_number}
    )

    return _to_doc_response(document)


@router.post("/{document_id}/reclassify", response_model=DocumentResponse)
def reclassify_document(
    document_id: str,
    data: DocumentReclassifyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Formally reclassifies a document (upgrade or downgrade security level).
    Enforces that the user has clearance for both the current and target classifications.
    Records full justification and provenance in the tamper-evident ledger.
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    effective_clearance = AccessControlService.get_effective_clearance(current_user)

    # User must have clearance for both current and target
    if not ClassificationLevel.can_access(effective_clearance, document.classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot reclassify: your clearance ({effective_clearance.value}) is insufficient for current level '{document.classification}'."
        )

    if not ClassificationLevel.can_access(effective_clearance, data.target_classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot reclassify: your clearance ({effective_clearance.value}) is insufficient for target level '{data.target_classification}'."
        )

    previous_classification = document.classification
    document.classification = data.target_classification.upper()
    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "action": "DOCUMENT_RECLASSIFICATION",
            "previous_classification": previous_classification,
            "new_classification": document.classification,
            "justification": data.justification,
            "document_number": document.document_number
        }
    )

    return _to_doc_response(document)


@router.post("/{document_id}/archive", response_model=DocumentResponse)
def archive_document(
    document_id: str,
    data: DocumentArchiveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Formally archives an active document, sealing its lifecycle state and establishing a retention period.
    """
    from datetime import datetime, timezone, timedelta

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.UPDATE.value)

    now = datetime.now(timezone.utc)
    document.status = DocumentStatus.ARCHIVED.value
    document.archived_at = now
    document.archival_reason = data.reason
    if data.retention_years:
        document.retention_until = now + timedelta(days=365 * data.retention_years)

    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "action": "DOCUMENT_ARCHIVED",
            "document_number": document.document_number,
            "archival_reason": data.reason,
            "retention_until": document.retention_until.isoformat() if document.retention_until else None
        }
    )

    return _to_doc_response(document)


@router.post("/{document_id}/unarchive", response_model=DocumentResponse)
def unarchive_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restores an archived document to active lifecycle status."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    if document.status != DocumentStatus.ARCHIVED.value:
        raise HTTPException(status_code=400, detail="Document is not in ARCHIVED status.")

    document.status = DocumentStatus.APPROVED.value if any(v.is_approved for v in document.versions) else DocumentStatus.DRAFT.value
    document.archived_at = None
    document.archival_reason = None
    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={"action": "DOCUMENT_UNARCHIVED", "document_number": document.document_number, "new_status": document.status}
    )

    return _to_doc_response(document)


@router.get("/{document_id}", response_model=DocumentDetail)
def get_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches document metadata and all versions after rigorous clearance evaluation."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    AuditService.record(
        db=db,
        action=ActionType.READ.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={"classification": document.classification}
    )

    detail = DocumentDetail.model_validate(document)
    if document.versions:
        detail.current_version = DocumentVersionResponse.model_validate(document.versions[0])
        detail.versions = [DocumentVersionResponse.model_validate(v) for v in document.versions]
    return detail


@router.get("/{document_id}/versions/{version_number}/download")
def download_document_version(
    document_id: str,
    version_number: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Streams file bytes to client, verifying disk integrity against SHA-256 fingerprint.
    If the file on disk was altered in any way, raises a critical integrity alarm!
    """
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    version = db.query(DocumentVersion).filter(
        DocumentVersion.document_id == document.id,
        DocumentVersion.version_number == version_number
    ).first()

    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")

    if not os.path.exists(version.file_path):
        raise HTTPException(status_code=500, detail="Vault storage error: file missing from storage path.")

    # Verify physical file integrity with stored SHA-256 fingerprint
    with open(version.file_path, "rb") as f:
        computed_sha256 = CryptoService.calculate_sha256_stream(f)

    if computed_sha256 != version.sha256_hash:
        # File has been tampered with or corrupted on disk!
        AuditService.record(
            db=db,
            action=ActionType.TAMPER_DETECTED.value,
            resource_type=ResourceType.DOCUMENT_VERSION.value,
            resource_id=version.id,
            actor=current_user,
            status="ALERT",
            details={
                "stored_fingerprint": version.sha256_hash,
                "disk_fingerprint": computed_sha256,
                "message": "CRITICAL: Physical file modification detected! Bitstream mismatch."
            }
        )
        raise HTTPException(
            status_code=500,
            detail="File integrity check failed! Cryptographic fingerprint does not match vault disk bytes."
        )

    AuditService.record(
        db=db,
        action=ActionType.DOWNLOAD.value,
        resource_type=ResourceType.DOCUMENT_VERSION.value,
        resource_id=version.id,
        actor=current_user,
        details={
            "version": version.version_number,
            "verified_sha256": computed_sha256
        }
    )

    return FileResponse(
        path=version.file_path,
        filename=version.original_filename,
        media_type=version.mime_type,
        headers={
            "X-Vault-SHA256": version.sha256_hash,
            "X-Vault-Version": str(version.version_number)
        }
    )


@router.get("/{document_id}/download")
def download_latest_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Downloads the latest active version of a document with cryptographic verification."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    if not document.versions:
        raise HTTPException(status_code=404, detail="Document has no uploaded versions.")

    latest_version = document.versions[0]
    return download_document_version(
        document_id=document.id,
        version_number=latest_version.version_number,
        db=db,
        current_user=current_user
    )


@router.delete("/{document_id}")
def delete_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Soft-deletes a document and moves it to the vault trash bin with audit tracking."""
    from datetime import datetime, timezone

    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.DELETE.value)

    document.is_deleted = True
    document.deleted_at = datetime.now(timezone.utc)
    document.deleted_by_id = current_user.id
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "action": "DOCUMENT_SOFT_DELETED",
            "document_number": document.document_number,
            "workspace_id": document.workspace_id
        }
    )

    return {"message": f"Document '{document.title}' ({document.document_number}) moved to trash."}


@router.post("/{document_id}/restore-deleted", response_model=DocumentResponse)
def restore_deleted_document(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Restores a soft-deleted document from the vault trash bin."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")

    AccessControlService.authorize_document(db, current_user, document, ActionType.READ.value)

    if not document.is_deleted:
        raise HTTPException(status_code=400, detail="Document is not in trash.")

    document.is_deleted = False
    document.deleted_at = None
    document.deleted_by_id = None
    db.commit()
    db.refresh(document)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DOCUMENT.value,
        resource_id=document.id,
        actor=current_user,
        details={
            "action": "DOCUMENT_RESTORED_FROM_TRASH",
            "document_number": document.document_number
        }
    )

    return _to_doc_response(document)
