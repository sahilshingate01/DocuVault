"""Temporary Security Clearance Schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TemporaryClearanceCreate(BaseModel):
    user_id: str
    granted_clearance: str  # e.g. "TOP_SECRET", "CONFIDENTIAL"
    workspace_id: Optional[str] = None
    document_id: Optional[str] = None
    reason: str
    valid_hours: int = 24  # default 24 hour delegation


class TemporaryClearanceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    user_id: str
    granted_by_id: Optional[str]
    granted_clearance: str
    workspace_id: Optional[str]
    document_id: Optional[str]
    reason: str
    valid_from: datetime
    valid_until: datetime
    is_revoked: bool
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None
    created_at: datetime

