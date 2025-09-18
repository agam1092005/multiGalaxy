from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas.user import (
    UserCreate, UserLogin, User as UserSchema, Token, 
    PasswordResetRequest, PasswordReset, EmailVerification,
    UserUpdate
)
from app.services.user_service import UserService
from app.core.auth import (
    create_access_token, get_current_active_user, 
    get_current_user, require_role
)
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()

@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(user_create: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    user_service = UserService(db)
    user = user_service.create_user(user_create)
    
    # TODO: Send verification email in production
    # For now, we'll just return the user
    
    return user

@router.post("/login", response_model=Token)
async def login(user_login: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return access token."""
    user_service = UserService(db)
    user = user_service.authenticate_user(user_login.email, user_login.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user account"
        )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.access_token_expire_minutes * 60,
        user=user
    )

@router.get("/me", response_model=UserSchema)
async def get_current_user_info(current_user: UserSchema = Depends(get_current_active_user)):
    """Get current user information."""
    return current_user

@router.put("/me", response_model=UserSchema)
async def update_current_user(
    user_update: UserUpdate,
    current_user: UserSchema = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user information."""
    user_service = UserService(db)
    return user_service.update_user(current_user.id, user_update)

@router.post("/verify-email")
async def verify_email(
    verification: EmailVerification,
    db: Session = Depends(get_db)
):
    """Verify user email with token."""
    user_service = UserService(db)
    user = user_service.verify_email(verification.token)
    
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
async def request_password_reset(
    request: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """Request password reset token."""
    user_service = UserService(db)
    reset_token = user_service.request_password_reset(request.email)
    
    # TODO: Send reset email in production
    # For now, we'll return success regardless
    
    return {"message": "If the email exists, a password reset link has been sent"}

@router.post("/reset-password")
async def reset_password(
    reset: PasswordReset,
    db: Session = Depends(get_db)
):
    """Reset password with token."""
    user_service = UserService(db)
    user = user_service.reset_password(reset.token, reset.new_password)
    
    return {"message": "Password reset successfully"}

@router.post("/logout")
async def logout(current_user: UserSchema = Depends(get_current_user)):
    """Logout user (client should discard token)."""
    # In a stateless JWT system, logout is handled client-side
    # In production, you might want to implement token blacklisting
    return {"message": "Logged out successfully"}

# Admin endpoints (for teachers/parents to manage users)
@router.get("/users", response_model=list[UserSchema])
async def list_users(
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(require_role(["teacher", "parent"]))
):
    """List users (teachers and parents only)."""
    from app.models.user import User as UserModel
    # Teachers can see all users, parents can see their children
    # This is a simplified implementation
    users = db.query(UserModel).filter(UserModel.is_active == True).all()
    return users

@router.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: UserSchema = Depends(require_role(["teacher"]))
):
    """Deactivate a user account (teachers only)."""
    user_service = UserService(db)
    user = user_service.deactivate_user(user_id)
    
    return {"message": f"User {user.email} deactivated successfully"}