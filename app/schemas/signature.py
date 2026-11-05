"""Signature schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SignDocumentRequest(BaseModel):
    private_key_pem: Optional[str] = None  # If provided, uses this private key; otherwise generates/uses bound key
    reason: Optional[str] = "Official endorsement and legal authorization"


class SignatureResponse(BaseModel):
    id: str
    signature_hex: str
    public_key_pem: str
    algorithm: str
    digest_signed: str
    signed_at: datetime
    signer_title: Optional[str]
    validity_status: str

    class Config:
        from_attributes = True


class SignatureVerificationResponse(BaseModel):
    is_valid: bool
    document_title: str
    version_number: int
    sha256_fingerprint: str
    signer_name: Optional[str]
    signer_title: Optional[str]
    signed_at: datetime
    algorithm: str
    message: str
