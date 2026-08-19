import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Numeric
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class CandlingStage(str, enum.Enum):
    DAY_10 = "DAY_10"
    DAY_18 = "DAY_18"
    DAY_25 = "DAY_25"


class CandlingSessionModel(Base):
    __tablename__ = "candling_sessions"

    session_id = Column(PGUUID(as_uuid=True), primary_key=True)
    batch_id = Column(String(64), ForeignKey("batches.batch_id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String(64), ForeignKey("devices.device_id", ondelete="RESTRICT"), nullable=False)
    stage = Column(Enum(CandlingStage), nullable=False)
    operator_name = Column(String(128), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)
    total_scanned = Column(Integer, nullable=False, default=0)
    fertile_count = Column(Integer, nullable=False, default=0)
    infertile_count = Column(Integer, nullable=False, default=0)
    abnormal_count = Column(Integer, nullable=False, default=0)
    avg_inference_ms = Column(Numeric(6, 2), nullable=False, default=0.00)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    batch = relationship("BatchModel", back_populates="sessions")
    device = relationship("DeviceModel", back_populates="sessions")
    scans = relationship("EggScanModel", back_populates="session", cascade="all, delete-orphan")
