"""ChainOfCustody model: Legal evidence custody tracking and transfer verification."""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel, get_utc_now


class ChainOfCustody(Base, TimeStampedModel):
    __tablename__ = "chain_of_custody"

    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Custody Transfer Participants
    sender_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    receiver_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    
    transfer_reason = Column(String(255), nullable=False)  # e.g., "Transfer to Forensic Ballistics Lab"
    custody_location = Column(String(200), nullable=False)  # e.g., "State Forensic Science Laboratory, Room 4"
    tamper_seal_number = Column(String(100), nullable=True)  # e.g., "SEAL-POL-99214-A"

    # Status: PENDING_ACCEPTANCE, ACCEPTED, REJECTED, ARCHIVED
    custody_status = Column(String(50), default="PENDING_ACCEPTANCE", nullable=False, index=True)

    # Verification of SHA-256 at time of receipt
    verified_sha256 = Column(String(64), nullable=False)
    is_integrity_verified = Column(Boolean, default=True, nullable=False)
    
    transferred_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)

    document_version = relationship("DocumentVersion")
    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
