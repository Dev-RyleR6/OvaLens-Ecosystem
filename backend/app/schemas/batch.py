from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.batch import DuckBreed, BatchStage, BatchStatus


class BatchCreate(BaseModel):
    batch_code: str = Field(..., min_length=3, max_length=64)
    breed: DuckBreed
    incubator_id: str = Field(..., max_length=64)
    initial_egg_count: int = Field(..., gt=0)
    set_date: datetime
    notes: Optional[str] = None


class BatchUpdate(BaseModel):
    incubator_id: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[BatchStatus] = None
    hatched_count: Optional[int] = None
    unhatched_count: Optional[int] = None


class AdvanceStagePayload(BaseModel):
    stage: BatchStage


class BatchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    batch_code: str
    breed: DuckBreed
    incubator_id: str
    initial_egg_count: int
    set_date: datetime
    target_hatch_date: datetime
    current_stage: BatchStage
    status: BatchStatus
    hatched_count: int
    unhatched_count: int
    notes: Optional[str]
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime


class BatchSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    batch_code: str
    breed: DuckBreed
    incubator_id: str
    initial_egg_count: int
    set_date: datetime
    target_hatch_date: datetime
    current_stage: BatchStage
    status: BatchStatus
    total_scanned: int = 0
    fertile_count: int = 0
    infertile_count: int = 0
    abnormal_count: int = 0
    fertility_rate: float = 0.0
    hatchability_rate: float = 0.0
