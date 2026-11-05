"""User identity and authorization credential model."""
from sqlalchemy import Column, String, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.constants import ClassificationLevel
from app.models.base import TimeStampedModel


class User(Base, TimeStampedModel):
    __tablename__ = "users"

    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    badge_number = Column(String(100), nullable=True)  # Officer/Staff ID e.g. "POL-SP-0402"
    
    # Specific individual clearance (bounded by position.max_clearance)
    clearance_level = Column(String(50), default=ClassificationLevel.UNCLASSIFIED.value, nullable=False)
    
    is_active = Column(Boolean, default=True, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)

    # Public cryptographic key (PEM format) for digital signature verification
    public_key_pem = Column(Text, nullable=True)

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)
    position_id = Column(String(36), ForeignKey("positions.id", ondelete="SET NULL"), nullable=True)

    organization = relationship("Organization", back_populates="users")
    department = relationship("Department", back_populates="users")
    position = relationship("Position", back_populates="users")
    
    signatures = relationship("DigitalSignature", back_populates="signer")
    audit_logs = relationship("AuditLog", back_populates="actor")
