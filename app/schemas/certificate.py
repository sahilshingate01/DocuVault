"""Cryptographic Certificate of Authenticity schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class CertificateVerificationResponse(BaseModel):
    certificate_id: str
    document_number: str
    document_title: str
    version_number: int
    classification: str
    sha256_fingerprint: str
    is_signed: bool
    signer_name: Optional[str] = None
    signer_title: Optional[str] = None
    signed_at: Optional[datetime] = None
    signature_algorithm: Optional[str] = None
    audit_block_sequence: int
    audit_entry_hash: str
    legal_admissibility_clause: str
    issued_at: datetime
    verification_status: str
