"""Document model: Governed file entity residing in a workspace."""
import json
from typing import List
from sqlalchemy import Column, String, Text, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.constants import ClassificationLevel, DocumentStatus
from app.models.base import TimeStampedModel


class Document(Base, TimeStampedModel):
    __tablename__ = "documents"

    title = Column(String(255), nullable=False, index=True)
    document_number = Column(String(100), unique=True, nullable=False, index=True)  # e.g., "DOC-FIR-2026-001"
    description = Column(Text, nullable=True)

    # Classification level of the document
    classification = Column(String(50), default=ClassificationLevel.UNCLASSIFIED.value, nullable=False, index=True)
    
    # Lifecycle status
    status = Column(String(50), default=DocumentStatus.DRAFT.value, nullable=False, index=True)

    # Searchable tags (JSON list: e.g. ["forensics", "ballistics", "homicide"])
    _tags = Column("tags", Text, default="[]")

    workspace_id = Column(String(36), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    workspace = relationship("Workspace", back_populates="documents")
    creator = relationship("User", foreign_keys=[created_by_id])
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan", order_by="DocumentVersion.version_number.desc()")

    @property
    def tags(self) -> List[str]:
        try:
            return json.loads(self._tags or "[]")
        except Exception:
            return []

    @tags.setter
    def tags(self, val: List[str]):
        self._tags = json.dumps(val or [])
