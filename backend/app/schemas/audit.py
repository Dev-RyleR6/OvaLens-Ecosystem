from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    log_id: int
    user_id: Optional[UUID] = None
    operator_name: Optional[str] = None
    action: str
    entity_type: str
    entity_id: str
    details: Dict[str, Any]
    ip_address: Optional[str] = None
    severity: str = "INFO"
    created_at: datetime
