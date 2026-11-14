"""Authentication Schemas."""
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserRegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organization_id: Optional[str] = None
    department_id: Optional[str] = None
    position_id: Optional[str] = None
    badge_number: Optional[str] = None


class Token(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    expires_in_minutes: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    new_password: str
    admin_token: Optional[str] = None


class TokenRefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
