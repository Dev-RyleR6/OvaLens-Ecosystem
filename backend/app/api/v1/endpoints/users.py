from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import UserModel, UserRole
from app.models.audit import AuditLogModel
from app.schemas.auth import UserResponse, UserCreate
from app.core.security import get_password_hash
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["Users"])


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
