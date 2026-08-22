from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class HatcherySettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    setting_id: UUID
    facility_name: str
    institution: str
    penoy_unit_price_php: float
    duckling_unit_price_php: float
    electricity_kwh_rate_php: float
    kwh_saved_per_culled_egg: float
    confidence_threshold: float
    conveyor_speed_cm_s: float
    conveyor_distance_cm: float
    updated_at: datetime


class HatcherySettingsUpdate(BaseModel):
    facility_name: Optional[str] = Field(None, max_length=128)
    institution: Optional[str] = Field(None, max_length=128)
    penoy_unit_price_php: Optional[float] = Field(None, ge=0.0)
    duckling_unit_price_php: Optional[float] = Field(None, ge=0.0)
    electricity_kwh_rate_php: Optional[float] = Field(None, ge=0.0)
    kwh_saved_per_culled_egg: Optional[float] = Field(None, ge=0.0)
    confidence_threshold: Optional[float] = Field(None, ge=0.1, le=1.0)
    conveyor_speed_cm_s: Optional[float] = Field(None, ge=1.0, le=100.0)
    conveyor_distance_cm: Optional[float] = Field(None, ge=1.0, le=200.0)
