from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.audit import AuditLogModel
from app.models.user import UserModel
from app.schemas.audit import AuditLogResponse
from app.api.deps import get_current_user

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("", response_model=List[AuditLogResponse], summary="List system audit logs")
def list_audit_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user)
):
    query = db.query(AuditLogModel)
    if action:
        query = query.filter(AuditLogModel.action == action)
    if entity_type:
        query = query.filter(AuditLogModel.entity_type == entity_type)

    return query.order_by(AuditLogModel.created_at.desc()).limit(limit).all()
