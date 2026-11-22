"""User Administration & Role Assignment Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType, ClassificationLevel
from app.core.security import get_password_hash
from app.models.user import User
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserAssignRequest,
    UserPermissionsUpdate,
)
from app.api.deps import get_current_user
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService

router = APIRouter(prefix="/users", tags=["User Management"])


@router.get("", response_model=List[UserResponse])
def list_users(
    organization_id: Optional[str] = Query(None, description="Filter by organization ID"),
    department_id: Optional[str] = Query(None, description="Filter by department ID"),
    position_id: Optional[str] = Query(None, description="Filter by position ID"),
    clearance_level: Optional[str] = Query(None, description="Filter by security clearance"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name, email, or badge number"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists organization users with multi-tier administrative filters."""
    query = db.query(User)

    if not current_user.is_admin:
        query = query.filter(User.organization_id == current_user.organization_id)
    elif organization_id:
        query = query.filter(User.organization_id == organization_id)

    if department_id:
        query = query.filter(User.department_id == department_id)
    if position_id:
        query = query.filter(User.position_id == position_id)
    if clearance_level:
        query = query.filter(User.clearance_level == clearance_level.upper())
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if search:
        query = query.filter(
            (User.full_name.ilike(f"%{search}%")) |
            (User.email.ilike(f"%{search}%")) |
            (User.badge_number.ilike(f"%{search}%"))
        )

    return query.order_by(User.full_name.asc()).all()


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new user with assigned organization, department, position, and cryptographic credentials."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to create users.")

    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Email '{data.email}' already exists.")

    org = db.query(Organization).filter(Organization.id == data.organization_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    if data.department_id:
        dept = db.query(Department).filter(Department.id == data.department_id).first()
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found.")

    clearance = data.clearance_level
    if data.position_id:
        pos = db.query(Position).filter(Position.id == data.position_id).first()
        if not pos:
            raise HTTPException(status_code=404, detail="Position not found.")
        clearance = pos.max_clearance

    # Generate public/private RSA identity keypair
    _, public_pem = CryptoService.generate_keypair()

    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=get_password_hash(data.password),
        badge_number=data.badge_number,
        clearance_level=clearance,
        is_active=data.is_active,
        is_admin=data.is_admin,
        public_key_pem=public_pem,
        organization_id=data.organization_id,
        department_id=data.department_id,
        position_id=data.position_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=current_user,
        details={
            "created_user_email": user.email,
            "organization_id": user.organization_id,
            "clearance_level": user.clearance_level
        }
    )

    return user


@router.get("/{user_id}", response_model=UserResponse)
def get_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches full profile, organizational role, and permissions of a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    if not current_user.is_admin and user.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Cross-organization view prohibited.")

    return user


@router.put("/{user_id}", response_model=UserResponse)
def update_user(
    user_id: str,
    data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates general user profile information."""
    if not current_user.is_admin and current_user.id != user_id and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to update user.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=current_user,
        details={"updated_fields": list(update_dict.keys()), "target_user": user.email}
    )

    return user


@router.put("/{user_id}/assign", response_model=UserResponse)
def assign_user(
    user_id: str,
    data: UserAssignRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Assigns user to an organization, department, and custom position/designation."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to assign roles and departments.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.organization_id = data.organization_id
    user.department_id = data.department_id
    user.position_id = data.position_id

    if data.clearance_level:
        user.clearance_level = data.clearance_level
    elif data.position_id:
        pos = db.query(Position).filter(Position.id == data.position_id).first()
        if pos:
            user.clearance_level = pos.max_clearance

    db.commit()
    db.refresh(user)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=current_user,
        details={
            "action": "ASSIGN_ORGANIZATION_AND_ROLE",
            "target_user": user.email,
            "organization_id": user.organization_id,
            "department_id": user.department_id,
            "position_id": user.position_id,
            "clearance_level": user.clearance_level
        }
    )

    return user


@router.put("/{user_id}/permissions", response_model=UserResponse)
def update_user_permissions(
    user_id: str,
    data: UserPermissionsUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates user security clearance level and administrative status."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Administrator privilege required to alter permissions.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(user, key, value)

    db.commit()
    db.refresh(user)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=current_user,
        details={"action": "UPDATE_USER_PERMISSIONS", "target_user": user.email, "changes": update_dict}
    )

    return user


@router.delete("/{user_id}")
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivates a user account."""
    if not current_user.is_admin and (not current_user.position or not current_user.position.can_manage_users):
        raise HTTPException(status_code=403, detail="Permission denied to deactivate users.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    user.is_active = False
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=current_user,
        details={"action": "DEACTIVATE_USER", "target_user": user.email}
    )

    return {"message": f"User '{user.full_name}' deactivated successfully."}

