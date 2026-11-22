"""Organization Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class OrganizationBase(BaseModel):
    name: str
    slug: str
    code: Optional[str] = None
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: bool = True


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    code: Optional[str] = None
    description: Optional[str] = None
    jurisdiction: Optional[str] = None
    contact_email: Optional[str] = None
    is_active: Optional[bool] = None


class OrganizationResponse(OrganizationBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    created_at: datetime
    updated_at: datetime
    department_count: int = 0
    user_count: int = 0
    workspace_count: int = 0

