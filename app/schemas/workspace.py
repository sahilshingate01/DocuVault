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


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    department_id: Optional[str] = None
    is_closed: bool
    created_at: datetime
    document_count: Optional[int] = 0
