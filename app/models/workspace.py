"""Workspace model: Containers for cases, projects, and dossiers."""
from sqlalchemy import Column, String, Text, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.constants import ClassificationLevel
from app.models.base import TimeStampedModel


class Workspace(Base, TimeStampedModel):
    __tablename__ = "workspaces"

    name = Column(String(200), nullable=False, index=True)
    code = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "CASE-2026-0402"
    description = Column(Text, nullable=True)
    workspace_type = Column(String(50), default="CASE", nullable=False)  # CASE, PROJECT, INQUIRY
    
    # Base classification tier of the workspace
    classification = Column(String(50), default=ClassificationLevel.UNCLASSIFIED.value, nullable=False)
    is_closed = Column(Boolean, default=False, nullable=False)

    organization_id = Column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    department_id = Column(String(36), ForeignKey("departments.id", ondelete="SET NULL"), nullable=True)

    organization = relationship("Organization", back_populates="workspaces")
    department = relationship("Department", back_populates="workspaces")
    documents = relationship("Document", back_populates="workspace", cascade="all, delete-orphan")
