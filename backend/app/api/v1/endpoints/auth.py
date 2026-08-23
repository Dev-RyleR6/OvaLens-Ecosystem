import time
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import UserModel, UserRole
from app.schemas.auth import UserLogin, UserCreate, UserResponse, Token
from app.api.deps import get_current_user, require_admin

router = APIRouter(prefix="/auth", tags=["Authentication"])

# In-memory sliding window IP rate limiter (10 attempts per minute)
_login_attempts = defaultdict(list)
MAX_LOGIN_ATTEMPTS = 10
RATE_LIMIT_WINDOW = 60


def _check_rate_limit(ip: str):
    now = time.time()
    attempts = [t for t in _login_attempts[ip] if now - t < RATE_LIMIT_WINDOW]
    _login_attempts[ip] = attempts
    if len(attempts) >= MAX_LOGIN_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed login attempts. Please wait 60 seconds before trying again."
        )


@router.post("/login", response_model=Token, summary="User login & JWT token retrieval")
def login(payload: UserLogin, request: Request, db: Session = Depends(get_db)):
    from app.models.audit import AuditLogModel
    client_ip = request.client.host if request.client else "127.0.0.1"
    _check_rate_limit(client_ip)

    user = db.query(UserModel).filter(UserModel.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        _login_attempts[client_ip].append(time.time())
        # Log security audit for failed attempt
        try:
            audit = AuditLogModel(
                user_id=user.user_id if user else None,
                action="USER_LOGIN_FAILED",
                entity_type="AUTH",
                entity_id=payload.email.strip().lower(),
                details={"reason": "Invalid credentials", "email": payload.email.strip().lower(), "severity": "SECURITY"},
                ip_address=client_ip
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

    # Successful login: reset attempts
    _login_attempts.pop(client_ip, None)

    # Log successful login
    try:
        audit = AuditLogModel(
            user_id=user.user_id,
            action="USER_LOGIN_SUCCESS",
            entity_type="AUTH",
            entity_id=str(user.user_id),
            details={"email": user.email, "role": user.role.value, "severity": "INFO"},
            ip_address=client_ip
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
