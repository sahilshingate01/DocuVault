"""Authentication and Identity Endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.auth import LoginRequest
from app.schemas.user import UserLoginResponse, UserResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=UserLoginResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate with email and password to receive a bearer JWT token."""
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
    
    token = create_access_token(subject=user.id)
    return UserLoginResponse(
        token=token,
        token_type="bearer",
        user=user
    )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    """Fetch current user identity, clearance level, organization, and permissions."""
    return current_user
