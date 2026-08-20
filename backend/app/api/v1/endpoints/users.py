from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import UserModel, UserRole
from app.schemas.auth import UserResponse, UserCreate
from app.core.security import get_password_hash
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=List[UserResponse], summary="List all hatchery operators & managers")
def list_users(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    return db.query(UserModel).order_by(UserModel.created_at.desc()).all()


@router.post("", response_model=UserResponse, summary="Admin registers a new user")
def create_user(
    payload: UserCreate,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    existing = db.query(UserModel).filter(UserModel.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User with this email already exists.")

    new_user = UserModel(
        email=payload.email,
        hashed_password=get_password_hash(payload.password),
        full_name=payload.full_name,
        role=payload.role,
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.patch("/{user_id}/status", response_model=UserResponse, summary="Toggle active status of a user")
def toggle_user_status(
    user_id: UUID,
    db: Session = Depends(get_db),
    admin: UserModel = Depends(require_admin)
):
    user = db.query(UserModel).filter(UserModel.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    return user
