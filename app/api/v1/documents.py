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
from app.schemas.document import DocumentResponse, DocumentDetail, DocumentVersionResponse
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
        media_type=version.mime_type
    )
