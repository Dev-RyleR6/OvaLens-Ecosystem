import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, Enum, Numeric, Integer
from sqlalchemy.orm import relationship
from app.core.database import Base


class DeviceStatus(str, enum.Enum):
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    SCANNING = "SCANNING"
    ERROR = "ERROR"


class DeviceModel(Base):
    __tablename__ = "devices"

    device_id = Column(String(64), primary_key=True)
    device_name = Column(String(128), nullable=False)
    ip_address = Column(String(45), nullable=True)
    hardware_platform = Column(String(64), nullable=False, default="Raspberry Pi 5")
    model_version = Column(String(64), nullable=False, default="yolov8n-onnx-v1.0")
    status = Column(Enum(DeviceStatus), nullable=False, default=DeviceStatus.OFFLINE)
    last_heartbeat = Column(DateTime(timezone=True), nullable=True)
    conveyor_speed_cm_s = Column(Numeric(5, 2), nullable=False, default=10.00)
    conveyor_dist_cm = Column(Numeric(5, 2), nullable=False, default=25.00)
    servo_pulse_ms = Column(Integer, nullable=False, default=250)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    sessions = relationship("CandlingSessionModel", back_populates="device")
