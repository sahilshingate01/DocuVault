"""AuditLog model: Tamper-evident cryptographic hash-chained audit trail."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel, get_utc_now


class AuditLog(Base, TimeStampedModel):
    __tablename__ = "audit_logs"

    # Monotonically increasing sequence / block height
    sequence_number = Column(Integer, unique=True, nullable=False, index=True)
    
    timestamp = Column(DateTime(timezone=True), default=get_utc_now, nullable=False, index=True)

    # Cryptographic Hash Chain: SHA-256(previous_hash + payload)
    previous_hash = Column(String(64), nullable=False)
    entry_hash = Column(String(64), unique=True, nullable=False, index=True)

    # Actor identity snapshot at time of event
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    user_email = Column(String(255), nullable=True)
    user_name = Column(String(255), nullable=True)
    user_position = Column(String(150), nullable=True)
    organization_id = Column(String(36), nullable=True)

    action = Column(String(50), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True, index=True)
    
    status = Column(String(50), default="SUCCESS", nullable=False)  # SUCCESS, DENIED, ERROR
    ip_address = Column(String(50), nullable=True)
    details_json = Column(Text, default="{}")

    actor = relationship("User", back_populates="audit_logs")
