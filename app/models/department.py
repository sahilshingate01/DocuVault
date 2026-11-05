"""Department organizational unit model."""
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.models.base import TimeStampedModel


class Department(Base, TimeStampedModel):
    __tablename__ = "departments"

    name = Column(String(150), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)

    organization = relationship("Organization", back_populates="departments")
    positions = relationship("Position", back_populates="department", cascade="all, delete-orphan")
    users = relationship("User", back_populates="department")
    workspaces = relationship("Workspace", back_populates="department")
