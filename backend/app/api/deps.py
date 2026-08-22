from typing import Generator, Optional
from uuid import UUID
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import UserModel, UserRole

# Edge Station Header Auth
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# Web Dashboard Bearer Token Auth
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login", auto_error=False)


def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    """Verifies that an incoming machine request possesses the valid Edge API Key."""
    if not api_key or api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing X-API-Key header. Access denied."
        )
    return api_key


def get_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> UserModel:
    """Extracts and validates the active user from the JWT Bearer token."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated. Provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials or token expired.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    try:
        user_id = UUID(payload["sub"])
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject.")

    user = db.query(UserModel).filter(UserModel.user_id == user_id, UserModel.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found or inactive.")
    return user


def get_optional_current_user(
    db: Session = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[UserModel]:
    """Optionally extracts the current user from JWT token without raising 401."""
    if not token:
        return None
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        return None
    try:
        user_id = UUID(payload["sub"])
        return db.query(UserModel).filter(UserModel.user_id == user_id, UserModel.is_active == True).first()
    except Exception:
        return None


def require_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Restricts access to System Administrators."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Administrator privileges.")
    return current_user


def require_manager_or_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """Restricts access to Farm Managers or Admins."""
    if current_user.role not in (UserRole.ADMIN, UserRole.MANAGER):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires Manager or Administrator privileges.")
    return current_user
