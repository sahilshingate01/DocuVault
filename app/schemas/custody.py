"""Chain of Custody schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.user import UserResponse


class CustodyTransferRequest(BaseModel):
    version_id: str
    receiver_id: str
    transfer_reason: str
    custody_location: str
    tamper_seal_number: Optional[str] = None
    notes: Optional[str] = None


class CustodyAcceptRequest(BaseModel):
    verification_notes: Optional[str] = "Physical seal intact, digital SHA-256 fingerprint verified."


class CustodyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_version_id: str
    sender_id: Optional[str]
    receiver_id: Optional[str]
    transfer_reason: str
    custody_location: str
    tamper_seal_number: Optional[str]
    custody_status: str
    verified_sha256: str
    is_integrity_verified: bool
    transferred_at: datetime
    accepted_at: Optional[datetime]
    notes: Optional[str]
    
    sender: Optional[UserResponse] = None
    receiver: Optional[UserResponse] = None
