"""DigitalSignature model: Cryptographic proof of authorization and non-repudiation."""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel, get_utc_now


class DigitalSignature(Base, TimeStampedModel):
    __tablename__ = "digital_signatures"

    signature_hex = Column(Text, nullable=False)
    public_key_pem = Column(Text, nullable=False)
    algorithm = Column(String(50), default="RSA-PSS-SHA256", nullable=False)
    
    # The exact SHA-256 document fingerprint that was signed
    digest_signed = Column(String(64), nullable=False, index=True)
    
    signed_at = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    signer_title = Column(String(150), nullable=True)  # e.g., "Superintendent of Police", "District Judge"
    validity_status = Column(String(50), default="VALID", nullable=False)

    document_version_id = Column(String(36), ForeignKey("document_versions.id", ondelete="CASCADE"), nullable=False)
    signer_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    document_version = relationship("DocumentVersion", back_populates="signatures")
    signer = relationship("User", back_populates="signatures")
