"""Version Diffing and Statement Integrity schemas."""
from typing import List, Optional
from pydantic import BaseModel


class LineDiff(BaseModel):
    line_number_v1: Optional[int]
    line_number_v2: Optional[int]
    operation: str  # "ADD", "DELETE", "EQUAL", "MODIFY"
    content: str


class DocumentDiffResponse(BaseModel):
    document_id: str
    document_title: str
    version_1: int
    version_2: int
    v1_sha256: str
    v2_sha256: str
    similarity_ratio: float  # e.g., 0.94 (94% identical)
    total_lines_v1: int
    total_lines_v2: int
    lines_added: int
    lines_deleted: int
    lines_modified: int
    unified_diff: str
    line_by_line: List[LineDiff]
    tampering_assessment: str
