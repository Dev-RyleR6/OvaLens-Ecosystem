from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.batch import DuckBreed, BatchStage, BatchStatus


class BatchCreate(BaseModel):
    batch_code: str = Field(..., min_length=3, max_length=64)
    breed: DuckBreed
    incubator_id: str = Field(..., max_length=64)
    initial_egg_count: int = Field(..., gt=0)
    set_date: datetime
    notes: Optional[str] = None


class EdgeBatchRegister(BatchCreate):
    model_config = ConfigDict(from_attributes=True, extra="forbid")
    batch_id: str = Field(..., min_length=1, max_length=64)
    device_id: str = Field(..., min_length=1, max_length=64)
    operator_name: str = Field(..., min_length=1, max_length=100)
    initial_egg_count: int = Field(..., gt=0, le=1000000, strict=True)
    notes: Optional[str] = Field(None, max_length=2000)

    @field_validator("batch_id", "batch_code", "incubator_id", "device_id", "operator_name", mode="before")
    @classmethod
    def nonblank(cls, value):
        if not isinstance(value, str):
            return value
        value = value.strip()
        if not value:
            raise ValueError("Must not be blank")
        return value

    @field_validator("set_date")
    @classmethod
    def actual_set_date(cls, value):
        if value.tzinfo is None:
            raise ValueError("Set date must include its timezone")
        from datetime import timezone, timedelta
        farm_zone = timezone(timedelta(hours=8))
        if value.astimezone(farm_zone).date() > datetime.now(farm_zone).date():
            raise ValueError("Incubation set date cannot be in the future")
        return value


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
    hatched_count: int = 0
    unhatched_count: int = 0
    total_scanned: int = 0
    fertile_count: int = 0
    infertile_count: int = 0
    manual_review_count: int = 0
    fertility_rate: float = 0.0
    hatchability_rate: float = 0.0
    notes: Optional[str] = None
    elapsed_days: int = 0
    milestone_alert: Optional[str] = None


class FinalizeHatchPayload(BaseModel):
    hatched_count: int = Field(..., ge=0)
    unhatched_count: Optional[int] = Field(None, ge=0)
    notes: Optional[str] = None


class SessionSummaryItem(BaseModel):
    session_id: UUID
    stage: str
    operator_name: str
    started_at: datetime
    total_scanned: int
    fertile_count: int
    infertile_count: int
    manual_review_count: int = 0
    fertility_rate: float
    avg_inference_ms: float


class BatchAnalyticsResponse(BaseModel):
    batch_id: str
    batch_code: str
    breed: DuckBreed
    incubator_id: str
    initial_egg_count: int
    set_date: datetime
    target_hatch_date: datetime
    current_stage: BatchStage
    status: BatchStatus
    elapsed_days: int
    
    # Quantitative Breakdown
    total_scanned_day_10: int
    fertile_day_10: int
    infertile_penoy_day_10: int
    manual_review_day_10: int = 0
    day_10_fertility_rate: float
    
    # Financial Salvage
    penoy_salvage_value_php: float
    electricity_saved_php: float
    projected_duckling_revenue_php: float
    
    # Hatching Metrics
    hatched_count: int
    unhatched_count: int
    actual_hatchability_rate: float
    
    # Candling Runs
    sessions: List[SessionSummaryItem]


class MilestoneCheckResponse(BaseModel):
    evaluated_batches: int
    updated_batches: int
    alerts: List[dict]


class BatchForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    batch_id: str
    batch_code: str
    breed: DuckBreed
    initial_egg_count: int
    elapsed_days: int
    current_stage: BatchStage
    status: BatchStatus

    # Biological Indicators
    detected_fertility_rate: float
    breed_baseline_fertility: float
    expected_embryo_viability_rate: float

    # Day 28 Predictions
    predicted_hatched_count: int
    predicted_hatchability_rate: float
    predicted_unhatched_count: int

    # Financial Forecast
    penoy_realized_revenue_php: float
    projected_duckling_revenue_php: float
    projected_total_revenue_php: float

    # Anomaly Diagnostics
    anomaly_status: str  # OPTIMAL | WARNING | CRITICAL
    confidence_level: str  # HIGH | MEDIUM | LOW
    advisory_notes: List[str]
