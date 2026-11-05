"""Authentication Schemas."""
from typing import Optional, List
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class TokenData(BaseModel):
    user_id: Optional[str] = None
