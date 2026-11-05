"""Document and Version schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class SignatureBrief(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    signer_title: Optional[str]
    signed_at: datetime
    algorithm: str
    validity_status: str
    digest_signed: str


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
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


class DocumentBase(BaseModel):
    title: str
    document_number: str
    description: Optional[str] = None
    classification: str = "UNCLASSIFIED"
    tags: List[str] = []


class DocumentCreate(DocumentBase):
    workspace_id: str


class DocumentResponse(DocumentBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    workspace_id: str
    status: str
    created_at: datetime
    current_version: Optional[DocumentVersionResponse] = None


class DocumentDetail(DocumentResponse):
    versions: List[DocumentVersionResponse] = []
