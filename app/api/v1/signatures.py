"""Digital Signature Endpoints: Approval workflows, cryptographic signing, and verification."""
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, DocumentStatus
from app.models.user import User
from app.models.document import Document
from app.models.document_version import DocumentVersion
from app.models.signature import DigitalSignature
from app.schemas.signature import SignDocumentRequest, SignatureResponse, SignatureVerificationResponse
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.crypto_service import CryptoService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/signatures", tags=["Signatures"])


@router.post("/approve/{version_id}")
def approve_version(
    version_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Formally approves a document version.
    Only positions with 'can_approve' authority may approve versions.
    """
    version = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")

    doc = version.document
    AccessControlService.authorize_document(db, current_user, doc, ActionType.APPROVE.value)

    if not current_user.position or not current_user.position.can_approve:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Position '{current_user.position.title if current_user.position else 'Staff'}' cannot approve documents."
        )

    now = datetime.now(timezone.utc)
    version.is_approved = True
    version.approved_at = now
    version.approved_by_id = current_user.id
    doc.status = DocumentStatus.APPROVED.value

    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.APPROVE.value,
        resource_type=ResourceType.DOCUMENT_VERSION.value,
        resource_id=version.id,
        actor=current_user,
        details={
            "document_title": doc.title,
            "version_number": version.version_number,
            "sha256": version.sha256_hash
        }
    )

    return {
        "message": f"Version {version.version_number} approved successfully.",
        "approved_at": now.isoformat(),
        "approver": current_user.full_name
    }


@router.post("/sign/{version_id}", response_model=SignatureResponse)
def sign_document_version(
    version_id: str,
    request: SignDocumentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Digitally signs an approved document version with an RSA-PSS asymmetric key.
    Enforces that:
    1. The version has been approved.
    2. The signer holds 'can_sign' privilege (e.g. Judge, Superintendent of Police, CEO).
    3. The exact SHA-256 fingerprint is signed.
    """
    version = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
    if not version:
        raise HTTPException(status_code=404, detail="Document version not found.")

    doc = version.document
    AccessControlService.authorize_document(db, current_user, doc, ActionType.SIGN.value)

    if not version.is_approved:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot sign an unapproved version. Document version must be approved prior to signing."
        )

    if not current_user.position or not current_user.position.can_sign:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Position '{current_user.position.title if current_user.position else 'Staff'}' does not hold digital signing authority."
        )

    # Use provided key or generate dedicated official signing keypair
    if request.private_key_pem:
        private_pem = request.private_key_pem
        if not current_user.public_key_pem:
            # derive public key or require bound key
            _, public_pem = CryptoService.generate_keypair()
        else:
            public_pem = current_user.public_key_pem
    else:
        # Generate an official keypair for this officer if not already created
        private_pem, public_pem = CryptoService.generate_keypair()
        if not current_user.public_key_pem:
            current_user.public_key_pem = public_pem
            db.commit()

    # Create cryptographic signature over the SHA-256 fingerprint of the file
    signature_hex = CryptoService.sign_digest(private_pem, version.sha256_hash)

    sig_record = DigitalSignature(
        signature_hex=signature_hex,
        public_key_pem=public_pem,
        algorithm="RSA-PSS-SHA256",
        digest_signed=version.sha256_hash,
        signer_title=current_user.position.title if current_user.position else "Authorized Signer",
        validity_status="VALID",
        document_version_id=version.id,
        signer_id=current_user.id
    )
    db.add(sig_record)
    doc.status = DocumentStatus.SIGNED.value
    db.commit()
    db.refresh(sig_record)

    AuditService.record(
        db=db,
        action=ActionType.SIGN.value,
        resource_type=ResourceType.SIGNATURE.value,
        resource_id=sig_record.id,
        actor=current_user,
        details={
            "document_number": doc.document_number,
            "version_number": version.version_number,
            "signed_fingerprint": version.sha256_hash,
            "signature_id": sig_record.id
        }
    )

    return sig_record


@router.get("/verify/{signature_id}", response_model=SignatureVerificationResponse)
def verify_digital_signature(
    signature_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Mathematically verifies a digital signature:
    - Checks that signature_hex was created by public_key_pem over digest_signed.
    - Validates digest_signed matches current version's SHA-256 hash.
    """
    sig = db.query(DigitalSignature).filter(DigitalSignature.id == signature_id).first()
    if not sig:
        raise HTTPException(status_code=404, detail="Signature record not found.")

    version = sig.document_version
    doc = version.document

    AccessControlService.authorize_document(db, current_user, doc, ActionType.READ.value)

    # 1. Cryptographic math verification
    is_valid = CryptoService.verify_signature(
        public_key_pem=sig.public_key_pem,
        sha256_digest=sig.digest_signed,
        signature_hex=sig.signature_hex
    )

    # 2. Check if the version's current fingerprint still matches what was signed
    fingerprint_match = (sig.digest_signed == version.sha256_hash)
    valid = is_valid and fingerprint_match

    message = (
        "Signature is cryptographically authentic and mathematically verified against public key."
        if valid else
        "SIGNATURE COMPROMISED: Fingerprint or cryptographic signature mismatch detected!"
    )

    AuditService.record(
        db=db,
        action=ActionType.VERIFY_SIGNATURE.value,
        resource_type=ResourceType.SIGNATURE.value,
        resource_id=sig.id,
        actor=current_user,
        details={"verification_result": valid, "document_id": doc.id}
    )

    return SignatureVerificationResponse(
        is_valid=valid,
        document_title=doc.title,
        version_number=version.version_number,
        sha256_fingerprint=version.sha256_hash,
        signer_name=sig.signer.full_name if sig.signer else "Unknown",
        signer_title=sig.signer_title,
        signed_at=sig.signed_at,
        algorithm=sig.algorithm,
        message=message
    )
