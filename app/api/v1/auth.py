"""Authentication and Identity Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    revoke_token,
)
from app.models.user import User
from app.models.organization import Organization
from app.models.department import Department
from app.models.position import Position
from app.schemas.auth import LoginRequest, RefreshTokenRequest, TokenRefreshResponse, UserRegisterRequest
from app.schemas.user import UserLoginResponse, UserResponse
from app.api.deps import get_current_user
from app.services.audit_service import AuditService
from app.services.crypto_service import CryptoService
from app.core.constants import ActionType, ResourceType, ClassificationLevel

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserLoginResponse, status_code=status.HTTP_201_CREATED)
def register(request: UserRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new user account with cryptographic identity, validation, and role assignment."""
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long."
        )

    # Check for existing email
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists."
        )

    # Resolve or create organization
    org_id = request.organization_id
    if org_id:
        org = db.query(Organization).filter(Organization.id == org_id).first()
        if not org:
            raise HTTPException(status_code=404, detail="Specified organization not found.")
    else:
        default_org = db.query(Organization).first()
        if not default_org:
            default_org = Organization(
                name="Primary Organization",
                slug="primary-org",
                jurisdiction="Default Jurisdiction"
            )
            db.add(default_org)
            db.commit()
            db.refresh(default_org)
        org_id = default_org.id

    # Resolve position and clearance
    clearance = ClassificationLevel.UNCLASSIFIED.value
    if request.position_id:
        position = db.query(Position).filter(Position.id == request.position_id).first()
        if not position:
            raise HTTPException(status_code=404, detail="Specified position not found.")
        clearance = position.max_clearance

    # Generate RSA cryptographic keypair for identity provenance and signing
    _, public_pem = CryptoService.generate_keypair()

    new_user = User(
        email=request.email,
        full_name=request.full_name,
        hashed_password=get_password_hash(request.password),
        badge_number=request.badge_number,
        clearance_level=clearance,
        is_active=True,
        is_admin=False,
        public_key_pem=public_pem,
        organization_id=org_id,
        department_id=request.department_id,
        position_id=request.position_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record registration in immutable audit ledger
    AuditService.record(
        db=db,
        action=ActionType.WRITE.value,
        resource_type=ResourceType.USER.value,
        resource_id=new_user.id,
        actor=new_user,
        details={
            "action": "USER_REGISTRATION",
            "email": new_user.email,
            "organization_id": org_id,
            "clearance_level": clearance,
        }
    )

    access_token = create_access_token(subject=new_user.id)
    refresh_token = create_refresh_token(subject=new_user.id)

    return UserLoginResponse(
        token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=new_user
    )


@router.post("/login", response_model=UserLoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive bearer JWT access and refresh tokens."""
    user = db.query(User).filter(User.email == request.email).first()
    if not user or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password credentials."
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This user account has been disabled."
        )
    
    access_token = create_access_token(subject=user.id)
    refresh_token = create_refresh_token(subject=user.id)

    AuditService.record(
        db=db,
        action=ActionType.LOGIN.value,
        resource_type=ResourceType.USER.value,
        resource_id=user.id,
        actor=user,
        details={"email": user.email, "organization_id": user.organization_id}
    )

    return UserLoginResponse(
        token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=user
    )


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):
    """Validates refresh token and issues a new access token and rotated refresh token."""
    payload = decode_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid, expired, or revoked refresh token."
        )
    
    user_id = payload.get("sub")
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User associated with refresh token no longer exists or is inactive."
        )
    
    # Revoke old refresh token JTI to enforce rotation
    old_jti = payload.get("jti")
    if old_jti:
        revoke_token(old_jti)
    revoke_token(request.refresh_token)

    new_access_token = create_access_token(subject=user.id)
    new_refresh_token = create_refresh_token(subject=user.id)

    return TokenRefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer"
    )


@router.post("/logout")
def logout(
    request: RefreshTokenRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Revokes refresh token and terminates current session."""
    revoke_token(request.refresh_token)
    AuditService.record(
        db=db,
        action=ActionType.LOGOUT.value,
        resource_type=ResourceType.USER.value,
        resource_id=current_user.id,
        actor=current_user,
        details={"email": current_user.email}
    )
    return {"message": "Logged out successfully. Tokens revoked."}


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Fetch current user identity, clearance level, organization, and permissions."""
    return current_user
