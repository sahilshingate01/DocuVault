"""User Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict


class PositionBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    code: str
    max_clearance: str
    can_sign: bool
    can_approve: bool
    can_export: bool
    allowed_actions: List[str]


class DepartmentBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    code: str


class OrganizationBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    slug: str
    jurisdiction: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    badge_number: Optional[str] = None
    clearance_level: str
    is_active: bool = True
    is_admin: bool = False


class UserCreate(UserBase):
    password: str
    organization_id: str
    department_id: Optional[str] = None
    position_id: Optional[str] = None


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    badge_number: Optional[str] = None
    clearance_level: Optional[str] = None
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None
    organization_id: Optional[str] = None
    department_id: Optional[str] = None
    position_id: Optional[str] = None


class UserAssignRequest(BaseModel):
    organization_id: str
    department_id: Optional[str] = None
    position_id: Optional[str] = None
    clearance_level: Optional[str] = None


class UserPermissionsUpdate(BaseModel):
    clearance_level: Optional[str] = None
    is_admin: Optional[bool] = None
    is_active: Optional[bool] = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    department_id: Optional[str] = None
    position_id: Optional[str] = None
    public_key_pem: Optional[str] = None
    created_at: datetime
    
    organization: Optional[OrganizationBrief] = None
    department: Optional[DepartmentBrief] = None
    position: Optional[PositionBrief] = None


class UserLoginResponse(BaseModel):
    token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: UserResponse
