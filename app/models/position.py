"""Position role capability and authority model."""
import json
from typing import List
from sqlalchemy import Column, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base
from app.core.constants import ClassificationLevel
from app.models.base import TimeStampedModel


class Position(Base, TimeStampedModel):
    __tablename__ = "positions"

    title = Column(String(150), nullable=False, index=True)
    code = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)

    # Maximum classification level this position is authorized to access
    max_clearance = Column(String(50), default=ClassificationLevel.UNCLASSIFIED.value, nullable=False)

    # Special authorities
    can_sign = Column(Boolean, default=False, nullable=False)
    can_approve = Column(Boolean, default=False, nullable=False)
    can_export = Column(Boolean, default=False, nullable=False)
    can_manage_users = Column(Boolean, default=False, nullable=False)

    # JSON-encoded array of allowed actions e.g. ["READ", "WRITE", "APPROVE", "SIGN"]
    _allowed_actions = Column("allowed_actions", Text, default='["READ"]')

    department_id = Column(String(36), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)

    department = relationship("Department", back_populates="positions")
    users = relationship("User", back_populates="position")

    @property
    def allowed_actions(self) -> List[str]:
        try:
            return json.loads(self._allowed_actions or '["READ"]')
        except Exception:
            return ["READ"]

    @allowed_actions.setter
    def allowed_actions(self, actions: List[str]):
        self._allowed_actions = json.dumps(actions)
