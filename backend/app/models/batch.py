import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import relationship
from app.core.database import Base


class DuckBreed(str, enum.Enum):
    KAYUMANGGI = "KAYUMANGGI"
    ITIM = "ITIM"
    KHAKI = "KHAKI"


class BatchStage(str, enum.Enum):
    SETTING = "SETTING"
    DAY_10 = "DAY_10"
    DAY_18 = "DAY_18"
    DAY_25 = "DAY_25"
    HATCHED = "HATCHED"
    COMPLETED = "COMPLETED"


class BatchStatus(str, enum.Enum):
    INCUBATING = "INCUBATING"
    CANDLING_DUE = "CANDLING_DUE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class BatchModel(Base):
    __tablename__ = "batches"

    batch_id = Column(String(64), primary_key=True)
    batch_code = Column(String(64), unique=True, nullable=False, index=True)
    breed = Column(Enum(DuckBreed), nullable=False)
    incubator_id = Column(String(64), nullable=False)
    initial_egg_count = Column(Integer, nullable=False)
    set_date = Column(DateTime(timezone=True), nullable=False)
    target_hatch_date = Column(DateTime(timezone=True), nullable=False)
    current_stage = Column(Enum(BatchStage), nullable=False, default=BatchStage.SETTING)
    status = Column(Enum(BatchStatus), nullable=False, default=BatchStatus.INCUBATING, index=True)
    hatched_count = Column(Integer, nullable=False, default=0)
    unhatched_count = Column(Integer, nullable=False, default=0)
    notes = Column(Text, nullable=True)
    created_by = Column(PGUUID(as_uuid=True), ForeignKey("users.user_id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    creator = relationship("UserModel", back_populates="batches")
    sessions = relationship("CandlingSessionModel", back_populates="batch", cascade="all, delete-orphan")
    scans = relationship("EggScanModel", back_populates="batch", cascade="all, delete-orphan")
