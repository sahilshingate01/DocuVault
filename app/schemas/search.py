"""Search schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel
from app.schemas.document import DocumentResponse


class SearchFilter(BaseModel):
    query: Optional[str] = None
    workspace_id: Optional[str] = None
    classification: Optional[str] = None
    status: Optional[str] = None
    tag: Optional[str] = None
    sha256_hash: Optional[str] = None


class SearchResponse(BaseModel):
    total_matches: int
    query: Optional[str]
    results: List[DocumentResponse]
