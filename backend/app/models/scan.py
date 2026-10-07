import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, DateTime, Enum, ForeignKey, Numeric, Text, Index, Boolean
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from sqlalchemy.orm import relationship
from app.core.database import Base


class FertilityClass(str, enum.Enum):
    FERTILE = "FERTILE"
    INFERTILE = "INFERTILE"


class RoutingAction(str, enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"
    MANUAL_REVIEW = "MANUAL_REVIEW"


class EggScanModel(Base):
    __tablename__ = "egg_scans"

    scan_id = Column(PGUUID(as_uuid=True), primary_key=True)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("candling_sessions.session_id", ondelete="CASCADE"), nullable=False, index=True)
    batch_id = Column(String(64), ForeignKey("batches.batch_id", ondelete="CASCADE"), nullable=False, index=True)
    sequence_number = Column(Integer, nullable=False)
    final_class = Column(Enum(FertilityClass), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    inference_ms = Column(Integer, nullable=False)
    routing_action = Column(Enum(RoutingAction), nullable=False)
    image_url = Column(Text, nullable=True)
    thumbnail_url = Column(Text, nullable=True)
    detections = Column(JSONB, nullable=False, default=list)
    cradle_index = Column(Integer, nullable=True)
    aspect_ratio = Column(Numeric(4, 2), nullable=True)
    vascular_index = Column(Numeric(5, 3), nullable=True)
    is_overridden = Column(Boolean, nullable=False, default=False)
    override_reason = Column(Text, nullable=True)
    overridden_at = Column(DateTime(timezone=True), nullable=True)
    scanned_at = Column(DateTime(timezone=True), nullable=False)
    synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("CandlingSessionModel", back_populates="scans")
    batch = relationship("BatchModel", back_populates="scans")

    __table_args__ = (
        Index("idx_scans_batch_scanned", "batch_id", "scanned_at"),
        Index("idx_scans_session_class", "session_id", "final_class"),
        Index("idx_scans_class_conf", "final_class", "confidence"),
        Index("idx_scans_routing_action", "routing_action"),
        Index("idx_scans_is_overridden", "is_overridden"),
    )
