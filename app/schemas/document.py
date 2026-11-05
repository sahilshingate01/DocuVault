"""Document and Version schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class SignatureBrief(BaseModel):
    id: str
    signer_title: Optional[str]
    signed_at: datetime
    algorithm: str
    validity_status: str
    digest_signed: str

    class Config:
        from_attributes = True


class DocumentVersionResponse(BaseModel):
    id: str
    version_number: int
    original_filename: str
    file_size: int
    mime_type: str
    sha256_hash: str
    change_summary: Optional[str] = None
    is_approved: bool
    approved_at: Optional[datetime] = None
    created_at: datetime
    signatures: List[SignatureBrief] = []

    class Config:
        from_attributes = True


class DocumentBase(BaseModel):
    title: str
    document_number: str
    description: Optional[str] = None
    classification: str = "UNCLASSIFIED"
    tags: List[str] = []


class DocumentCreate(DocumentBase):
    workspace_id: str


class DocumentResponse(DocumentBase):
    id: str
    workspace_id: str
    status: str
    created_at: datetime
    current_version: Optional[DocumentVersionResponse] = None

    class Config:
        from_attributes = True


class DocumentDetail(DocumentResponse):
    versions: List[DocumentVersionResponse] = []
