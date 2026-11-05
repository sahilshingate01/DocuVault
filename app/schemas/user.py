"""User Schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class PositionBrief(BaseModel):
    id: str
    title: str
    code: str
    max_clearance: str
    can_sign: bool
    can_approve: bool
    can_export: bool
    allowed_actions: List[str]

    class Config:
        from_attributes = True


class DepartmentBrief(BaseModel):
    id: str
    name: str
    code: str

    class Config:
        from_attributes = True


class OrganizationBrief(BaseModel):
    id: str
    name: str
    slug: str
    jurisdiction: Optional[str] = None

    class Config:
        from_attributes = True


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


class UserResponse(UserBase):
    id: str
    organization_id: str
    department_id: Optional[str] = None
    position_id: Optional[str] = None
    public_key_pem: Optional[str] = None
    created_at: datetime
    
    organization: Optional[OrganizationBrief] = None
    department: Optional[DepartmentBrief] = None
    position: Optional[PositionBrief] = None

    class Config:
        from_attributes = True


class UserLoginResponse(BaseModel):
    token: str
    token_type: str = "bearer"
    user: UserResponse
