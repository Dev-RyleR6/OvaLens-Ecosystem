import hashlib
import hmac
import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Union, Any

from app.core.config import settings

try:
    # pyrefly: ignore [missing-import]
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    _HAVE_PASSLIB = True
except ImportError:
    _HAVE_PASSLIB = False

try:
    # pyrefly: ignore [missing-import]
    from jose import jwt, JWTError
    _HAVE_JOSE = True
except ImportError:
    _HAVE_JOSE = False


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hash."""
    if _HAVE_PASSLIB:
        try:
            return pwd_context.verify(plain_password, hashed_password)
        except Exception:
            pass
    # Fallback SHA-256 with salt
    if hashed_password.startswith("sha256$"):
        _, salt, hash_val = hashed_password.split("$")
        computed = hashlib.sha256((salt + plain_password).encode("utf-8")).hexdigest()
        return hmac.compare_digest(computed, hash_val)
    return False


def get_password_hash(password: str) -> str:
    """Generate a hash from a plain password."""
    if _HAVE_PASSLIB:
        try:
            return pwd_context.hash(password)
        except Exception:
            pass
    # Fallback salted sha256
    salt = "ovalens_salt"
    hash_val = hashlib.sha256((salt + password).encode("utf-8")).hexdigest()
    return f"sha256${salt}${hash_val}"


def create_access_token(subject: Union[str, Any], role: str, expires_delta: Optional[timedelta] = None) -> str:
    """Create a signed JWT access token."""
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(subject),
        "role": role,
        "exp": int(expire.timestamp()),
        "iat": int(datetime.now(timezone.utc).timestamp())
    }

    if _HAVE_JOSE:
        return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    else:
        # Minimal HMAC-SHA256 JWT Fallback
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).decode().rstrip("=")
        payload = base64.urlsafe_b64encode(json.dumps(to_encode).encode()).decode().rstrip("=")
        signature = hmac.new(
            settings.JWT_SECRET.encode(),
            f"{header}.{payload}".encode(),
            hashlib.sha256
        ).digest()
        sig_str = base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return f"{header}.{payload}.{sig_str}"


def decode_access_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT access token."""
    if _HAVE_JOSE:
        try:
            return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        except Exception:
            return None
    else:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts
            expected_sig = hmac.new(
                settings.JWT_SECRET.encode(),
                f"{header_b64}.{payload_b64}".encode(),
                hashlib.sha256
            ).digest()
            sig_padded = sig_b64 + "=" * (-len(sig_b64) % 4)
            if not hmac.compare_digest(base64.urlsafe_b64decode(sig_padded), expected_sig):
                return None
            payload_padded = payload_b64 + "=" * (-len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
            if payload.get("exp") and payload["exp"] < datetime.now(timezone.utc).timestamp():
                return None
            return payload
        except Exception:
            return None
