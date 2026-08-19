from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict
from app.models.scan import FertilityClass, RoutingAction


class DetectionBox(BaseModel):
    bbox: List[float] = Field(..., description="[x_center, y_center, width, height] normalized")
    confidence: float
    class_label: FertilityClass


class ScanSyncItem(BaseModel):
    scan_id: UUID
    session_id: UUID
    batch_id: str
    sequence_number: int
    final_class: FertilityClass
    confidence: float = Field(..., ge=0.0, le=1.0)
    inference_ms: int = Field(..., ge=0)
    routing_action: RoutingAction
    image_url: Optional[str] = None
    detections: List[Dict[str, Any]] = Field(default_factory=list)
    scanned_at: datetime


class ScanSyncPayload(BaseModel):
    scans: List[ScanSyncItem] = Field(..., min_length=1)


class ScanSyncResponse(BaseModel):
    status: str = "success"
    total_received: int
    synced_count: int
    duplicates_ignored: int
    session_id: Optional[UUID] = None


class ScanListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    session_id: UUID
    batch_id: str
    sequence_number: int
    final_class: FertilityClass
    confidence: float
    inference_ms: int
    routing_action: RoutingAction
    thumbnail_url: Optional[str]
    scanned_at: datetime


class ScanDetailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    scan_id: UUID
    session_id: UUID
    batch_id: str
    sequence_number: int
    final_class: FertilityClass
    confidence: float
    inference_ms: int
    routing_action: RoutingAction
    image_url: Optional[str]
    thumbnail_url: Optional[str]
    detections: List[Dict[str, Any]]
    scanned_at: datetime
    synced_at: datetime
