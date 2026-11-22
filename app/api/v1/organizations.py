"""Organization Management Endpoints."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.constants import ActionType, ResourceType
from app.models.user import User
from app.models.organization import Organization
from app.models.department import Department
from app.models.workspace import Workspace
from app.schemas.organization import (
    OrganizationCreate,
    OrganizationUpdate,
    OrganizationResponse,
)
from app.api.deps import get_current_user
from app.services.audit_service import AuditService

router = APIRouter(prefix="/organizations", tags=["Organizations"])


def _to_org_response(org: Organization, db: Session) -> OrganizationResponse:
    dept_count = db.query(Department).filter(Department.organization_id == org.id).count()
    user_count = db.query(User).filter(User.organization_id == org.id).count()
    ws_count = db.query(Workspace).filter(Workspace.organization_id == org.id).count()
    res = OrganizationResponse.model_validate(org)
    res.department_count = dept_count
    res.user_count = user_count
    res.workspace_count = ws_count
    return res


@router.get("", response_model=List[OrganizationResponse])
def list_organizations(
    search: Optional[str] = Query(None, description="Search by organization name or slug"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists organizations with multi-tenant filtering and resource counts."""
    query = db.query(Organization)
    if search:
        query = query.filter(
            (Organization.name.ilike(f"%{search}%")) | (Organization.slug.ilike(f"%{search}%"))
        )
    if is_active is not None:
        query = query.filter(Organization.is_active == is_active)

    orgs = query.order_by(Organization.name.asc()).all()
    return [_to_org_response(o, db) for o in orgs]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(
    data: OrganizationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Creates a new organization tenant."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only system administrators may create new organizations."
        )

    existing = db.query(Organization).filter(
        (Organization.name == data.name) | (Organization.slug == data.slug)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An organization with name '{data.name}' or slug '{data.slug}' already exists."
        )

    org = Organization(
        name=data.name,
        slug=data.slug,
        code=data.code,
        description=data.description,
        jurisdiction=data.jurisdiction,
        contact_email=data.contact_email,
        is_active=data.is_active
    )
    db.add(org)
    db.commit()
    db.refresh(org)

    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.ORGANIZATION.value if hasattr(ResourceType, "ORGANIZATION") else "ORGANIZATION",
        resource_id=org.id,
        actor=current_user,
        details={"name": org.name, "slug": org.slug}
    )

    return _to_org_response(org, db)


@router.get("/{org_id}", response_model=OrganizationResponse)
def get_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetches details and resource metrics for a specific organization."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")
    return _to_org_response(org, db)


@router.put("/{org_id}", response_model=OrganizationResponse)
def update_organization(
    org_id: str,
    data: OrganizationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Updates organization profile and configuration."""
    if not current_user.is_admin and current_user.organization_id != org_id:
        raise HTTPException(status_code=403, detail="Not authorized to modify this organization.")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    update_dict = data.model_dump(exclude_unset=True)
    for key, value in update_dict.items():
        setattr(org, key, value)

    db.commit()
    db.refresh(org)

    AuditService.record(
        db=db,
        action=ActionType.UPDATE.value,
        resource_type=ResourceType.ORGANIZATION.value if hasattr(ResourceType, "ORGANIZATION") else "ORGANIZATION",
        resource_id=org.id,
        actor=current_user,
        details={"updated_fields": list(update_dict.keys())}
    )

    return _to_org_response(org, db)


@router.delete("/{org_id}")
def delete_organization(
    org_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Deactivates an organization."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="System administrator privilege required.")

    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found.")

    org.is_active = False
    db.commit()

    AuditService.record(
        db=db,
        action=ActionType.DELETE.value,
        resource_type=ResourceType.ORGANIZATION.value if hasattr(ResourceType, "ORGANIZATION") else "ORGANIZATION",
        resource_id=org.id,
        actor=current_user,
        details={"name": org.name, "action": "DEACTIVATE"}
    )

    return {"message": f"Organization '{org.name}' deactivated successfully."}

