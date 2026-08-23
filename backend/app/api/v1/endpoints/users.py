from typing import List, Dict, Any
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import UserModel, UserRole
from app.models.audit import AuditLogModel
from app.schemas.auth import UserResponse, UserCreate, PasswordChangeRequest, ProfileUpdateRequest
from app.core.security import get_password_hash, verify_password
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.patch("/me/profile", response_model=UserResponse, summary="Update logged-in user profile")
def update_my_profile(
    payload: ProfileUpdateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    current_user.full_name = payload.full_name.strip()
    db.commit()
    db.refresh(current_user)

    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        audit = AuditLogModel(
            user_id=current_user.user_id,
            action="USER_PROFILE_UPDATED",
            entity_type="AUTH",
            entity_id=str(current_user.user_id),
            details={"full_name": current_user.full_name, "severity": "INFO"},
            ip_address=client_ip
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    return current_user


@router.patch("/me/password", response_model=Dict[str, Any], summary="Change logged-in user password")
def change_my_password(
    payload: PasswordChangeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password verification failed. Please enter your correct current password."
        )

    current_user.hashed_password = get_password_hash(payload.new_password)
    db.commit()

    client_ip = request.client.host if request.client else "127.0.0.1"
    try:
        audit = AuditLogModel(
            user_id=current_user.user_id,
            action="USER_PASSWORD_CHANGED",
            entity_type="AUTH",
            entity_id=str(current_user.user_id),
            details={"email": current_user.email, "severity": "SECURITY"},
            ip_address=client_ip
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    return {"status": "success", "message": "Password changed successfully."}


@router.get("", response_model=List[UserResponse], summary="List all hatchery operators & managers")
def list_users(
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    return db.query(UserModel).order_by(UserModel.created_at.desc()).all()


@router.post("", response_model=UserResponse, summary="Admin registers a new user")
def create_user(
    payload: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    existing = db.query(UserModel).filter(UserModel.email == payload.email.strip().lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists.")

    new_user = UserModel(
        email=payload.email.strip().lower(),
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name.strip(),
        role=payload.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Security audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLogModel(
        user_id=admin.user_id,
        action="USER_CREATED",
        entity_type="AUTH",
        entity_id=str(new_user.user_id),
        details={"created_email": new_user.email, "role": new_user.role.value, "created_by": admin.email, "severity": "INFO"},
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return new_user


@router.patch("/{user_id}/status", response_model=UserResponse, summary="Toggle active status of a user")
def toggle_user_status(
    user_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    if user_id == admin.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot suspend your own active administrator account."
        )

    user = db.query(UserModel).filter(UserModel.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)

    # Security audit log
    client_ip = request.client.host if request.client else "127.0.0.1"
    audit = AuditLogModel(
        user_id=admin.user_id,
        action="USER_STATUS_TOGGLED",
        entity_type="AUTH",
        entity_id=str(user.user_id),
        details={
            "target_email": user.email,
            "new_status": "ACTIVE" if user.is_active else "SUSPENDED",
            "modified_by": admin.email,
            "severity": "SECURITY" if not user.is_active else "INFO"
        },
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return user
