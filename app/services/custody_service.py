"""Chain of Custody Service: Manages forensic evidence transfer and verification."""
from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.core.constants import ActionType, ResourceType
from app.models.chain_of_custody import ChainOfCustody
from app.models.document_version import DocumentVersion
from app.models.user import User
from app.services.audit_service import AuditService
from app.services.access_control import AccessControlService


class CustodyService:
    @classmethod
    def initiate_transfer(
        cls,
        db: Session,
        sender: User,
        receiver_id: str,
        version_id: str,
        transfer_reason: str,
        custody_location: str,
        tamper_seal_number: Optional[str] = None,
        notes: Optional[str] = None
    ) -> ChainOfCustody:
        """Initiates a legal custody transfer for an evidence document version."""
        version = db.query(DocumentVersion).filter(DocumentVersion.id == version_id).first()
        if not version:
            raise HTTPException(status_code=404, detail="Document version not found.")

        # Check sender authority
        AccessControlService.authorize_document(db, sender, version.document, ActionType.READ.value)

        receiver = db.query(User).filter(User.id == receiver_id, User.is_active == True).first()
        if not receiver:
            raise HTTPException(status_code=404, detail="Designated receiving officer not found.")

        # Ensure receiver has adequate clearance for this document
        AccessControlService.authorize_document(db, receiver, version.document, ActionType.READ.value, record_audit=False)

        custody_entry = ChainOfCustody(
            document_version_id=version.id,
            sender_id=sender.id,
            receiver_id=receiver.id,
            transfer_reason=transfer_reason,
            custody_location=custody_location,
            tamper_seal_number=tamper_seal_number,
            custody_status="PENDING_ACCEPTANCE",
            verified_sha256=version.sha256_hash,
            is_integrity_verified=True,
            notes=notes
        )
        db.add(custody_entry)
        db.commit()
        db.refresh(custody_entry)

        AuditService.record(
            db=db,
            action="CUSTODY_TRANSFER_INITIATED",
            resource_type="CHAIN_OF_CUSTODY",
            resource_id=custody_entry.id,
            actor=sender,
            details={
                "document_title": version.document.title,
                "version_number": version.version_number,
                "receiver": receiver.full_name,
                "tamper_seal": tamper_seal_number,
                "sha256": version.sha256_hash
            }
        )
        return custody_entry

    @classmethod
    def accept_custody(
        cls,
        db: Session,
        receiver: User,
        custody_id: str,
        verification_notes: Optional[str] = None
    ) -> ChainOfCustody:
        """Receiver accepts custody after confirming file integrity and seal intactness."""
        entry = db.query(ChainOfCustody).filter(ChainOfCustody.id == custody_id).first()
        if not entry:
            raise HTTPException(status_code=404, detail="Custody record not found.")

        if entry.receiver_id != receiver.id and not receiver.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the designated receiving officer may accept this custody transfer."
            )

        if entry.custody_status != "PENDING_ACCEPTANCE":
            raise HTTPException(status_code=400, detail=f"Cannot accept custody with status '{entry.custody_status}'.")

        # Re-verify SHA-256 fingerprint matches document version
        version = entry.document_version
        if version.sha256_hash != entry.verified_sha256:
            entry.is_integrity_verified = False
            entry.custody_status = "REJECTED"
            db.commit()
            AuditService.record(
                db=db,
                action=ActionType.TAMPER_DETECTED.value,
                resource_type="CHAIN_OF_CUSTODY",
                resource_id=entry.id,
                actor=receiver,
                status="ALERT",
                details={"reason": "Custody SHA-256 mismatch detected upon transfer receipt."}
            )
            raise HTTPException(status_code=500, detail="CRITICAL: Hash mismatch detected during custody receipt!")

        now = datetime.now(timezone.utc)
        entry.custody_status = "ACCEPTED"
        entry.accepted_at = now
        if verification_notes:
            entry.notes = (entry.notes or "") + f" | Receiver Notes: {verification_notes}"

        db.commit()
        db.refresh(entry)

        AuditService.record(
            db=db,
            action="CUSTODY_ACCEPTED",
            resource_type="CHAIN_OF_CUSTODY",
            resource_id=entry.id,
            actor=receiver,
            details={
                "document_title": version.document.title,
                "version_number": version.version_number,
                "sha256_verified": entry.verified_sha256,
                "tamper_seal": entry.tamper_seal_number
            }
        )
        return entry

    @classmethod
    def get_document_timeline(cls, db: Session, document_id: str) -> List[ChainOfCustody]:
        """Returns the full chain of custody log for a document."""
        return db.query(ChainOfCustody).join(DocumentVersion).filter(
            DocumentVersion.document_id == document_id
        ).order_by(ChainOfCustody.created_at.asc()).all()
