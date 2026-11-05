"""Audit schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    id: str
    sequence_number: int
    timestamp: datetime
    previous_hash: str
    entry_hash: str
    user_email: Optional[str]
    user_name: Optional[str]
    user_position: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    status: str
    ip_address: Optional[str]
    details_json: str

    class Config:
        from_attributes = True


class AuditIntegrityResponse(BaseModel):
    is_valid: bool
    total_records: int
    latest_sequence: Optional[int] = None
    head_hash: Optional[str] = None
    message: str
    broken_at_sequence: Optional[int] = None
