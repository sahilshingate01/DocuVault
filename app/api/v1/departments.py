"""Department Management Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType
from app.models.user import User
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
)
from app.api.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/departments", tags=["Departments"])


def _to_dept_response(dept: Department, db: Session) -> DepartmentResponse:
    pos_count = db.query(Position).filter(Position.department_id == dept.id).count()
    user_count = db.query(User).filter(User.department_id == dept.id).count()
    res = DepartmentResponse.model_validate(dept)
    res.position_count = pos_count
    res.user_count = user_count
    return res


@router.get("", response_model=List[DepartmentResponse])
def list_departments(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    search: Optional[str] = Query(None, description="Search by name or code"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists departments filtered by organization and access criteria."""
    query = db.query(Department)

    # Multi-tenant boundary: non-admins see only their organization
    target_org = organization_id or current_user.organization_id
    if not current_user.is_admin:
        query = query.filter(Department.organization_id == current_user.organization_id)
    elif organization_id:
        query = query.filter(Department.organization_id == organization_id)

    if search:
        query = query.filter(
            (Department.name.ilike(f"%{search}%")) | (Department.code.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.filter(Department.is_active == is_active)

    depts = query.order_by(Department.name.asc()).all()
    return [_to_dept_response(d, db) for d in depts]


@router.post("", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    data: DepartmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new organizational department."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to create departments.")

    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    existing = db.query(Department).filter(
        Department.organization_id == data.organization_id,
        Department.code == data.code
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Department with code '{data.code}' already exists in this organization.")

    dept = Department(
        name=data.name,
        code=data.code,
        description=data.description,
        organization_id=data.organization_id,
        is_active=data.is_active
    )
    db.add(dept)
    db.commit()
    db.refresh(dept)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.DEPARTMENT.value,
        resource_id=dept.id,
        actor=current_user,
        details={"name": dept.name, "code": dept.code, "organization_id": dept.organization_id}
    )

    return _to_dept_response(dept, db)


@router.get("/{dept_id}", response_model=DepartmentResponse)
def get_department(
    dept_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches details for a specific department."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")
    return _to_dept_response(dept, db)


@router.put("/{dept_id}", response_model=DepartmentResponse)
def update_department(
    dept_id: str,
    data: DepartmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates department configuration."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    if not current_user.is_admin and (dept.organization_id != current_user.organization_id):
        raise HTTPException(status_code=403, detail="Cross-organization update prohibited.")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(dept, key, value)

    db.commit()
    db.refresh(dept)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.DEPARTMENT.value,
        resource_id=dept.id,
        actor=current_user,
        details={"updated_fields": list(update_dict.keys())}
    )

    return _to_dept_response(dept, db)


@router.delete("/{dept_id}")
def delete_department(
    dept_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivates a department."""
    dept = db.query(Department).filter(Department.id == dept_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found.")

    dept.is_active = False
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.DEPARTMENT.value,
        resource_id=dept.id,
        actor=current_user,
        details={"code": dept.code, "action": "DEACTIVATE"}
    )

    return {"message": f"Department '{dept.name}' deactivated successfully."}
