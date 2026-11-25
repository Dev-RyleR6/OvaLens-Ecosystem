from uuid import UUID
from pydantic import BaseModel, ConfigDict
from app.models.user import UserRole


class OperatorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    full_name: str
    role: UserRole
