"""Position and Custom Designation Management Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel
from app.models.user import User
from app.models.department import Department
from app.models.position import Position
from app.schemas.position import (
    PositionCreate,
    PositionUpdate,
    PositionResponse,
)
from app.api.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/positions", tags=["Positions & Designations"])


def _to_pos_response(pos: Position, db: Session) -> PositionResponse:
    user_count = db.query(User).filter(User.position_id == pos.id).count()
    res = PositionResponse.model_validate(pos)
    res.user_count = user_count
    return res


@router.get("", response_model=List[PositionResponse])
def list_positions(
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    designation_type: Optional[str] = Query(None, description="Filter by designation e.g. SP, JUDGE, CEO, MANAGER, EMPLOYEE"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists designations and custom organizational positions."""
    query = db.query(Position)
    if department_id:
        query = query.filter(Position.department_id == department_id)
    if designation_type:
        query = query.filter(Position.designation_type == designation_type.upper())
    if is_active is not None:
        query = query.filter(Position.is_active == is_active)

    positions = query.order_by(Position.title.asc()).all()
    return [_to_pos_response(p, db) for p in positions]


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
def create_position(
    data: PositionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Creates a new custom position or standard designation (SP, Judge, CEO, Manager, Employee).
    Configures clearance tier, digital signing authority, and allowed action matrix.
    """
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to create positions.")

    dept = db.query(Department).filter(Department.id == data.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    existing = db.query(Position).filter(
        Position.department_id == data.department_id,
        Position.code == data.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Position with code '{data.code}' already exists in this department.")

    position = Position(
        title=data.title,
        code=data.code,
        description=data.description,
        designation_type=data.designation_type.upper() if data.designation_type else "CUSTOM",
        max_clearance=data.max_clearance,
        can_sign=data.can_sign,
        can_approve=data.can_approve,
        can_export=data.can_export,
        can_manage_users=data.can_manage_users,
        allowed_actions=data.allowed_actions,
        department_id=data.department_id,
        is_active=data.is_active
    )
    db.add(position)
    db.commit()
    db.refresh(position)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.POSITION.value,
        resource_id=position.id,
        actor=current_user,
        details={
            "title": position.title,
            "code": position.code,
            "designation_type": position.designation_type,
            "max_clearance": position.max_clearance,
            "can_sign": position.can_sign,
            "can_approve": position.can_approve
        }
    )

    return _to_pos_response(position, db)


@router.get("/{pos_id}", response_model=PositionResponse)
def get_position(
    pos_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches details and privilege parameters for a specific position."""
    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found.")
    return _to_pos_response(pos, db)


@router.put("/{pos_id}", response_model=PositionResponse)
def update_position(
    pos_id: str,
    data: PositionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates position privileges, clearance levels, or action permissions."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to update positions.")

    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found.")

    update_dict = data.model_dump(exclude_unset=True)
    if "allowed_actions" in update_dict and update_dict["allowed_actions"] is not None:
        pos.allowed_actions = update_dict.pop("allowed_actions")

    if "designation_type" in update_dict and update_dict["designation_type"]:
        update_dict["designation_type"] = update_dict["designation_type"].upper()

    for key, value in update_dict.items():
        setattr(pos, key, value)

    db.commit()
    db.refresh(pos)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.POSITION.value,
        resource_id=pos.id,
        actor=current_user,
        details={"updated_fields": list(data.model_dump(exclude_unset=True).keys())}
    )

    return _to_pos_response(pos, db)


@router.delete("/{pos_id}")
def delete_position(
    pos_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivates a position."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to delete positions.")

    pos = db.query(Position).filter(Position.id == pos_id).first()
    if not pos:
        raise HTTPException(status_code=404, detail="Position not found.")

    pos.is_active = False
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.POSITION.value,
        resource_id=pos.id,
        actor=current_user,
        details={"code": pos.code, "action": "DEACTIVATE"}
    )

    return {"message": f"Position '{pos.title}' deactivated successfully."}

