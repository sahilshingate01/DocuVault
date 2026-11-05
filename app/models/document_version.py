"""DocumentVersion model: Immutable version records with SHA-256 fingerprinting."""
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, BigInteger, ForeignKey, DateTime, Boolean, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel


class DocumentVersion(Base, TimeStampedModel):
    __tablename__ = "document_versions"

    version_number = Column(Integer, nullable=False, default=1)
    file_path = Column(String(500), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_size = Column(BigInteger, nullable=False)  # in bytes
    mime_type = Column(String(100), default="application/octet-stream", nullable=False)

    # SHA-256 cryptographic fingerprint of the file contents
    sha256_hash = Column(String(64), nullable=False, index=True)

    change_summary = Column(Text, nullable=True)

    # Approval tracking
    is_approved = Column(Boolean, default=False, nullable=False)
    approved_at = Column(DateTime(timezone=True), nullable=True)
    approved_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    uploaded_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document = relationship("Document", back_populates="versions")
    uploaded_by = relationship("User", foreign_keys=[uploaded_by_id])
    approved_by = relationship("User", foreign_keys=[approved_by_id])
    signatures = relationship("DigitalSignature", back_populates="document_version", cascade="all, delete-orphan")
