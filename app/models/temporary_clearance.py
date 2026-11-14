"""TemporaryClearance model: Time-bound delegated access grants."""
from sqlalchemy import Column, String, Text, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel, get_utc_now


class TemporaryClearance(Base, TimeStampedModel):
    __tablename__ = "temporary_clearances"

    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    granted_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Granted clearance level (e.g. TOP_SECRET or CONFIDENTIAL)
    granted_clearance = Column(String(50), nullable=False)
    
    # Target scope: either specific workspace or specific document (or organization-wide if both null)
    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=True)
    document_id = Column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=True)

    reason = Column(Text, nullable=False)  # e.g., "Court-ordered defense counsel review in State vs Malgudi"
    
    valid_from = Column(DateTime(timezone=True), default=get_utc_now, nullable=False)
    valid_until = Column(DateTime(timezone=True), nullable=False, index=True)

    is_revoked = Column(Boolean, default=False, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(Text, nullable=True)

    user = relationship("User", foreign_keys=[user_id])
    granted_by = relationship("User", foreign_keys=[granted_by_id])
    workspace = relationship("Workspace")
    document = relationship("Document")

