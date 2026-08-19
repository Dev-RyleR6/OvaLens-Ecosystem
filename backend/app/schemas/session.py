from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.session import CandlingStage


class SessionCreate(BaseModel):
    session_id: UUID
    batch_id: str = Field(..., max_length=64)
    device_id: str = Field(..., max_length=64)
    stage: CandlingStage
    operator_name: str = Field(..., max_length=128)
    started_at: datetime


class SessionEnd(BaseModel):
    ended_at: datetime


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    batch_id: str
    device_id: str
    stage: CandlingStage
    operator_name: str
    started_at: datetime
    ended_at: Optional[datetime]
    total_scanned: int
    fertile_count: int
    infertile_count: int
    abnormal_count: int
    avg_inference_ms: float
    created_at: datetime
