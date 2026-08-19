from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict
from app.models.device import DeviceStatus


class DeviceRegister(BaseModel):
    device_id: str = Field(..., max_length=64)
    device_name: str = Field(..., max_length=128)
    hardware_platform: str = "Raspberry Pi 5"
    model_version: str = "yolov8n-onnx-v1.0"
    conveyor_speed_cm_s: float = 10.00
    conveyor_dist_cm: float = 25.00
    servo_pulse_ms: int = 250


class DeviceHeartbeat(BaseModel):
    ip_address: Optional[str] = None
    status: DeviceStatus = DeviceStatus.ONLINE


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    device_id: str
    device_name: str
    ip_address: Optional[str]
    hardware_platform: str
    model_version: str
    status: DeviceStatus
    last_heartbeat: Optional[datetime]
    conveyor_speed_cm_s: float
    conveyor_dist_cm: float
    servo_pulse_ms: int
    created_at: datetime
