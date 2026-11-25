from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.api.deps import verify_api_key
from app.core.database import get_db
from app.models.user import UserModel
from app.schemas.operator import OperatorResponse

router = APIRouter(prefix="/operators", tags=["Station operators"])


@router.get("", response_model=list[OperatorResponse], dependencies=[Depends(verify_api_key)])
def list_operators(db: Session = Depends(get_db)):
    """Minimal staff roster for attribution; selection does not authenticate a user."""
    return db.query(UserModel).filter(UserModel.is_active.is_(True)).order_by(
        UserModel.full_name, UserModel.user_id).all()
