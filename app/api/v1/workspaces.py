"""Workspace management endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate, WorkspaceResponse, WorkspaceDetailResponse
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService
from app.services.audit_service import AuditService

router = APIRouter(prefix="/workspaces", tags=["Workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists workspaces accessible to the user based on organization and clearance."""
    effective_clearance = AccessControlService.get_effective_clearance(current_user)
    workspaces = db.query(Workspace).filter(
        Workspace.organization_id == current_user.organization_id
    ).all()

    # Filter by user clearance
    accessible = []
    for ws in workspaces:
        if ClassificationLevel.can_access(effective_clearance, ws.classification):
            ws_dict = WorkspaceResponse.model_validate(ws)
            ws_dict.document_count = len(ws.documents)
            accessible.append(ws_dict)

    AuditService.record(
        db=db,
        action=ActionType.READ.value,
        resource_type=ResourceType.WORKSPACE.value,
        actor=current_user,
        details={"result_count": len(accessible)}
    )
    return accessible


@router.post("", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
def create_workspace(
    data: WorkspaceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new workspace (Case, Project, or Dossier)."""
    if not AccessControlService.can_perform_action(current_user, ActionType.WRITE.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your position does not have permission to create workspaces."
        )

    # Clearance check for creating classified workspaces
    effective_clearance = AccessControlService.get_effective_clearance(current_user)
    if not ClassificationLevel.can_access(effective_clearance, data.classification):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Cannot create workspace classified as '{data.classification}': your clearance is '{effective_clearance.value}'."
        )

    existing = db.query(Workspace).filter(Workspace.code == data.code).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Workspace code '{data.code}' already exists."
        )

    workspace = Workspace(
        name=data.name,
        code=data.code,
        description=data.description,
        workspace_type=data.workspace_type,
        classification=data.classification,
        organization_id=current_user.organization_id,
        department_id=data.department_id or current_user.department_id
    )
    db.add(workspace)
    db.commit()
    db.refresh(workspace)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.WORKSPACE.value,
        resource_id=workspace.id,
        actor=current_user,
        details={"workspace_code": workspace.code, "classification": workspace.classification}
    )

    res = WorkspaceResponse.model_validate(workspace)
    res.document_count = 0
    return res


@router.get("/{workspace_id}", response_model=WorkspaceDetailResponse)
def get_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Retrieves workspace metadata, statistical metrics, and security classification breakdown."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    AccessControlService.authorize_workspace(db, current_user, workspace, ActionType.READ.value)

    res = WorkspaceDetailResponse.model_validate(workspace)
    res.document_count = len(workspace.documents)

    total_versions = 0
    total_size_bytes = 0
    class_breakdown = {}

    for doc in workspace.documents:
        class_breakdown[doc.classification] = class_breakdown.get(doc.classification, 0) + 1
        total_versions += len(doc.versions)
        for ver in doc.versions:
            total_size_bytes += ver.file_size or 0

    res.total_versions = total_versions
    res.total_size_bytes = total_size_bytes
    res.total_size_mb = round(total_size_bytes / (1024 * 1024), 2)
    res.classification_breakdown = class_breakdown

    return res


@router.put("/{workspace_id}", response_model=WorkspaceDetailResponse)
def update_workspace(
    workspace_id: str,
    data: WorkspaceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates workspace details, classification, or archive/closure status."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    AccessControlService.authorize_workspace(db, current_user, workspace, ActionType.WRITE.value)

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(workspace, key, value)

    db.commit()
    db.refresh(workspace)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.WORKSPACE.value,
        resource_id=workspace.id,
        actor=current_user,
        details={"workspace_code": workspace.code, "updated_fields": list(update_dict.keys())}
    )

    return get_workspace(workspace_id=workspace.id, db=db, current_user=current_user)


@router.delete("/{workspace_id}")
def delete_or_close_workspace(
    workspace_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Closes or archives an active workspace."""
    workspace = db.query(Workspace).filter(Workspace.id == workspace_id).first()
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found.")

    AccessControlService.authorize_workspace(db, current_user, workspace, ActionType.DELETE.value)

    workspace.is_closed = True
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.WORKSPACE.value,
        resource_id=workspace.id,
        actor=current_user,
        details={"workspace_code": workspace.code, "action": "CLOSE_WORKSPACE"}
    )

    return {"message": f"Workspace '{workspace.name}' ({workspace.code}) closed successfully."}
