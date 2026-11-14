"""Security Authorization Engine and Policy Evaluation Endpoints."""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ClassificationLevel, ActionType, ResourceType
from app.models.user import User
from app.models.document import Document
from app.schemas.security import (
    AccessEvaluationRequest,
    AccessEvaluationResponse,
    UserPermissionMatrix,
)
from app.api.deps import get_current_user
from app.services.access_control import AccessControlService

router = APIRouter(prefix="/security", tags=["Security & Authorization Engine"])


@router.post("/evaluate", response_model=AccessEvaluationResponse)
def evaluate_access(
    data: AccessEvaluationRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Real-time ABAC Permission Evaluation Engine:
    Evaluates multi-attribute policy parameters (Subject, Resource, Action, Environment)
    and returns an explicit ALLOW or DENY determination with an exhaustive rule trace.
    """
    user_to_evaluate = current_user
    if data.target_user_id and current_user.is_admin:
        simulated = db.query(User).filter(User.id == data.target_user_id).first()
        if simulated:
            user_to_evaluate = simulated

    result = AccessControlService.evaluate_abac_policy(
        db=db,
        user=user_to_evaluate,
        action=data.action.upper(),
        resource_type=data.resource_type.upper(),
        resource_id=data.resource_id
    )

    return AccessEvaluationResponse(**result)


@router.get("/permissions/my", response_model=UserPermissionMatrix)
def get_my_permission_matrix(
    current_user: User = Depends(get_current_user)
):
    """Returns the caller's effective access capability matrix and accessible classification tiers."""
    effective_clearance = AccessControlService.get_effective_clearance(current_user)
    permitted_classifications = [
        c.value for c in ClassificationLevel if ClassificationLevel.can_access(effective_clearance, c)
    ]

    return UserPermissionMatrix(
        user_id=current_user.id,
        email=current_user.email,
        clearance_level=current_user.clearance_level,
        effective_clearance=effective_clearance.value,
        is_admin=current_user.is_admin,
        position_title=current_user.position.title if current_user.position else None,
        designation_type=getattr(current_user.position, "designation_type", None) if current_user.position else None,
        can_sign=current_user.position.can_sign if current_user.position else False,
        can_approve=current_user.position.can_approve if current_user.position else False,
        can_export=current_user.position.can_export if current_user.position else False,
        can_manage_users=current_user.position.can_manage_users if current_user.position else False,
        allowed_actions=current_user.position.allowed_actions if current_user.position else ["READ"],
        permitted_classifications=permitted_classifications
    )


@router.get("/validate-document/{document_id}")
def validate_document_access(
    document_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Pre-flight check returning all permitted operations for this user on a specific document."""
    doc = db.query(Document).filter(Document.id == document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    actions = [
        ActionType.READ.value,
        ActionType.UPDATE.value,
        ActionType.DOWNLOAD.value,
        ActionType.APPROVE.value,
        ActionType.SIGN.value,
        ActionType.DELETE.value,
    ]

    operation_rights = {}
    for action in actions:
        res = AccessControlService.evaluate_abac_policy(
            db=db,
            user=current_user,
            action=action,
            resource_type=ResourceType.DOCUMENT.value,
            resource_id=doc.id
        )
        operation_rights[action] = res["allowed"]

    return {
        "document_id": doc.id,
        "document_number": doc.document_number,
        "classification": doc.classification,
        "operation_rights": operation_rights
    }
