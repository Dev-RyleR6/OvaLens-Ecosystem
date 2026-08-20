from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import UserModel, UserRole
from app.schemas.auth import UserLogin, UserCreate, UserResponse, Token
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=Token, summary="User login & JWT token retrieval")
def login(payload: UserLogin, db: Session = Depends(get_db)):
    from app.models.audit import AuditLogModel
    user = db.query(UserModel).filter(UserModel.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Log security audit for failed attempt
        try:
            audit = AuditLogModel(
                user_id=user.user_id if user else None,
                action="USER_LOGIN_FAILED",
                entity_type="AUTH",
                entity_id=payload.email.strip().lower(),
                details={"reason": "Invalid credentials", "email": payload.email.strip().lower()},
                ip_address="127.0.0.1"
            )
            db.add(audit)
            db.commit()
        except Exception:
            db.rollback()

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is deactivated. Contact hatchery administrator.")

    # Log successful login
    try:
        audit = AuditLogModel(
            user_id=user.user_id,
            action="USER_LOGIN_SUCCESS",
            entity_type="AUTH",
            entity_id=str(user.user_id),
            details={"email": user.email, "role": user.role.value},
            ip_address="127.0.0.1"
        )
        db.add(audit)
        db.commit()
    except Exception:
        db.rollback()

    token = create_access_token(subject=user.user_id, role=user.role.value)
    return Token(access_token=token, token_type="bearer", user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse, summary="Get current logged in user")
def get_me(current_user: UserModel = Depends(get_current_user)):
    return current_user


@router.post("/register", response_model=UserResponse, summary="Admin creates a new user account")
def register_user(
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
        role=payload.role
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user
