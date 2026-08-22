import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Numeric, DateTime
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from app.core.database import Base


class HatcherySettingsModel(Base):
    __tablename__ = "hatchery_settings"

    setting_id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    facility_name = Column(String(128), nullable=False, default="Foundation University Automated Hatchery")
    institution = Column(String(128), nullable=False, default="Foundation University - Dumaguete City")
    
    # Economic Parameters (Philippine Peso)
    penoy_unit_price_php = Column(Numeric(6, 2), nullable=False, default=14.00)
    duckling_unit_price_php = Column(Numeric(6, 2), nullable=False, default=40.00)
    electricity_kwh_rate_php = Column(Numeric(6, 2), nullable=False, default=12.50)
    kwh_saved_per_culled_egg = Column(Numeric(6, 4), nullable=False, default=0.2000)
    
    # AI & Sorter Parameters
    confidence_threshold = Column(Numeric(4, 3), nullable=False, default=0.850)
    conveyor_speed_cm_s = Column(Numeric(5, 2), nullable=False, default=10.00)
    conveyor_distance_cm = Column(Numeric(5, 2), nullable=False, default=25.00)
    
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
