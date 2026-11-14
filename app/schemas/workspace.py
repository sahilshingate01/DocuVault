"""Workspace schemas."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict


class WorkspaceBase(BaseModel):
    name: str
    code: str
    description: Optional[str] = None
    workspace_type: str = "CASE"
    classification: str = "UNCLASSIFIED"


class WorkspaceCreate(WorkspaceBase):
    department_id: Optional[str] = None


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    workspace_type: Optional[str] = None
    classification: Optional[str] = None
    department_id: Optional[str] = None
    is_closed: Optional[bool] = None


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    department_id: Optional[str] = None
    is_closed: bool
    created_at: datetime
    document_count: Optional[int] = 0


class WorkspaceDetailResponse(WorkspaceResponse):
    total_versions: int = 0
    total_size_bytes: int = 0
    total_size_mb: float = 0.0
    classification_breakdown: dict = {}
