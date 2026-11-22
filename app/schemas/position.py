"""Position and Designation Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.core.constants import ClassificationLevel


class PositionBase(BaseModel):
    title: str
    code: str
    description: Optional[str] = None
    designation_type: Optional[str] = "CUSTOM"  # SP, JUDGE, CEO, MANAGER, EMPLOYEE, CUSTOM
    max_clearance: str = ClassificationLevel.UNCLASSIFIED.value
    can_sign: bool = False
    can_approve: bool = False
    can_export: bool = False
    can_manage_users: bool = False
    allowed_actions: List[str] = ["READ"]
    department_id: str
    is_active: Optional[bool] = True


class PositionCreate(PositionBase):
    pass


class PositionUpdate(BaseModel):
    title: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    designation_type: Optional[str] = None
    max_clearance: Optional[str] = None
    can_sign: Optional[bool] = None
    can_approve: Optional[bool] = None
    can_export: Optional[bool] = None
    can_manage_users: Optional[bool] = None
    allowed_actions: Optional[List[str]] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None


class PositionResponse(PositionBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
    user_count: int = 0

