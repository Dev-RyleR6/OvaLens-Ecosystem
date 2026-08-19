import enum
import os
from datetime import datetime, timezone
from typing import List, Optional
from urllib.parse import quote_plus
from uuid import UUID

import uvicorn

# pyrefly: ignore [missing-import] this ignore is for the pyrefly extension
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query, status, File, UploadFile, Form
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from sqlalchemy import (
    create_engine, Column, String, Integer, Numeric, DateTime, Enum, BigInteger, ForeignKey, func, desc, text, case
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import declarative_base, sessionmaker, Session, relationship, selectinload

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

DB_USER = os.getenv("DB_USER", "postgres")
DB_PASS = os.getenv("DB_PASS")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "hatchery_db")
API_KEY = os.getenv("API_KEY")

if not DB_PASS:
    raise RuntimeError("DB_PASS environment variable is required. Create a .env file or set it in your shell before starting the server.")
if not API_KEY:
    raise RuntimeError("API_KEY environment variable is required. Create a .env file or set it in your shell before starting the server.")

DATABASE_URL = f"postgresql://{DB_USER}:{quote_plus(DB_PASS)}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ==============================================================================
# ENUMS & SQLALCHEMY ORM MODELS
# ==============================================================================
class DuckBreed(str, enum.Enum):
    KAYUMANGGI = "KAYUMANGGI"
    ITIM = "ITIM"
    KHAKI = "KHAKI"

class CandlingStage(str, enum.Enum):
    DAY_10 = "DAY_10"
    DAY_18 = "DAY_18"
    DAY_25 = "DAY_25"

class FertilityClass(str, enum.Enum):
    FERTILE = "FERTILE"
    INFERTILE = "INFERTILE"
    ABNORMAL = "ABNORMAL"

class RoutingAction(str, enum.Enum):
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"

class BatchStatus(str, enum.Enum):
    """Lifecycle stages of an incubation batch."""
    SETTING = "SETTING"
    INCUBATING = "INCUBATING"
    CANDLING_DUE = "CANDLING_DUE"
    HATCHING = "HATCHING"
    COMPLETED = "COMPLETED"

class SessionModel(Base):
    __tablename__ = "sessions"
    session_id = Column(PGUUID(as_uuid=True), primary_key=True)
    batch_code = Column(String(64), nullable=False)
    breed_code = Column(Enum(DuckBreed), nullable=False)
    stage = Column(Enum(CandlingStage), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False)
    ended_at = Column(DateTime(timezone=True), nullable=True)

    scans = relationship("ScanModel", back_populates="session", cascade="all, delete-orphan")

class ScanModel(Base):
    __tablename__ = "scans"
    scan_id = Column(PGUUID(as_uuid=True), primary_key=True)
    session_id = Column(PGUUID(as_uuid=True), ForeignKey("sessions.session_id"), nullable=False)
    breed_code = Column(Enum(DuckBreed), nullable=False)
    final_class = Column(Enum(FertilityClass), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    inference_ms = Column(Integer, nullable=False)
    routing_action = Column(Enum(RoutingAction), nullable=False)
    image_url = Column(String, nullable=True)
    scanned_at = Column(DateTime(timezone=True), nullable=False)
    synced_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    session = relationship("SessionModel", back_populates="scans")
    detections = relationship("DetectionModel", back_populates="scan", cascade="all, delete-orphan")

class DetectionModel(Base):
    __tablename__ = "detections"
    detection_id = Column(BigInteger, primary_key=True, autoincrement=True)
    scan_id = Column(PGUUID(as_uuid=True), ForeignKey("scans.scan_id"), nullable=False)
    class_label = Column(Enum(FertilityClass), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    bbox_x_center = Column(Numeric(6, 5), nullable=False)
    bbox_y_center = Column(Numeric(6, 5), nullable=False)
    bbox_width = Column(Numeric(6, 5), nullable=False)
    bbox_height = Column(Numeric(6, 5), nullable=False)

    scan = relationship("ScanModel", back_populates="detections")


class BatchModel(Base):
    """Represents an incubation batch (a set of eggs loaded on a specific date)."""
    __tablename__ = "batches"
    batch_id = Column(String(64), primary_key=True)
    breed = Column(String(64), nullable=False)
    set_date = Column(DateTime(timezone=True), nullable=False)
    incubation_day = Column(Integer, nullable=False, default=0)
    status = Column(Enum(BatchStatus), nullable=False, default=BatchStatus.INCUBATING)
    incubator_id = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    candling_scans = relationship("CandlingScanModel", back_populates="batch", cascade="all, delete-orphan")


class CandlingScanModel(Base):
    """Per-egg candling classification result submitted by OvaLens edge devices."""
    __tablename__ = "candling_scans"
    candling_scan_id = Column(BigInteger, primary_key=True, autoincrement=True)
    batch_id = Column(String(64), ForeignKey("batches.batch_id"), nullable=False)
    tray_id = Column(String(64), nullable=False)
    egg_position = Column(String(16), nullable=False)
    classification = Column(String(32), nullable=False)
    confidence = Column(Numeric(5, 4), nullable=False)
    operator_id = Column(String(64), nullable=True)
    scanned_at = Column(DateTime(timezone=True), nullable=False)

    batch = relationship("BatchModel", back_populates="candling_scans")

# Create all tables now that every model class has been defined
Base.metadata.create_all(bind=engine)

# ==============================================================================
# FASTAPI STATIC FILES FOR DASHBOARD
# ==============================================================================
app = FastAPI(
    title="OvaLens Hatchery API",
    version="1.1.0",
    description="Central Backend API for OvaLens Duck Egg Candling & Analytics System.",
    swagger_ui_parameters={"persistAuthorization": True},
)

app.mount("/dashboard/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "dashboard")), name="dashboard_static")

# ==============================================================================
# PYDANTIC SCHEMAS
# ==============================================================================
class DetectionPayload(BaseModel):
    class_label: FertilityClass
    confidence: float
    bbox: List[float] = Field(..., description="[x_center, y_center, width, height] normalized")

class ScanSyncPayload(BaseModel):
    scan_id: UUID
    session_id: UUID
    batch_code: str
    stage: CandlingStage
    breed_code: DuckBreed
    final_class: FertilityClass
    confidence: float
    inference_ms: int
    scanned_at: datetime
    routing_action: Optional[RoutingAction] = None
    image_url: Optional[str] = None
    detections: List[DetectionPayload] = Field(default_factory=list)

class DetectionResponse(BaseModel):
    detection_id: int
    class_label: FertilityClass
    confidence: float
    bbox: List[float]

    class Config:
        from_attributes = True

class SessionCreatePayload(BaseModel):
    session_id: UUID
    batch_code: str
    breed_code: DuckBreed
    stage: CandlingStage

class SessionEndPayload(BaseModel):
    ended_at: datetime


# ---- Batch & Candling Schemas ------------------------------------------------
class ActiveBatchResponse(BaseModel):
    """Response item for GET /api/v1/batches/active."""
    batch_id: str
    breed: str
    set_date: datetime
    incubation_day: int
    status: BatchStatus

    class Config:
        from_attributes = True


class CandlingScanItem(BaseModel):
    """A single egg classification inside a candling submission."""
    tray_id: str = Field(..., description="Tray identifier, e.g. 'TRAY-A'")
    egg_position: str = Field(..., description="Grid position on the tray, e.g. 'A3'")
    classification: str = Field(
        ...,
        description="Vision model result: 'fertile', 'infertile', or 'early_dead'"
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0,
        description="Model confidence score between 0.0 and 1.0"
    )


class CandlingScanPayload(BaseModel):
    """Top-level request body for POST /api/v1/candling/scans."""
    batch_id: str = Field(..., description="Must reference an existing active batch")
    scanned_at: datetime = Field(..., description="ISO 8601 timestamp of the scan")
    operator_id: Optional[str] = Field(None, description="ID of the operator performing the scan")
    scans: List[CandlingScanItem] = Field(
        ..., min_length=1,
        description="Array of per-egg classification results"
    )


class CandlingScanSummaryResponse(BaseModel):
    """Success response returned after recording candling scans."""
    status: str
    batch_id: str
    total_scans_recorded: int
    classification_summary: dict
    scanned_at: datetime
    external_sync_status: Optional[str] = None
    external_sync_record_id: Optional[str] = None

class ScanDetailResponse(BaseModel):
    scan_id: UUID
    session_id: UUID
    breed_code: DuckBreed
    final_class: FertilityClass
    confidence: float
    inference_ms: int
    routing_action: RoutingAction
    image_url: Optional[str]
    scanned_at: datetime
    synced_at: datetime
    detections: List[DetectionResponse]

class ScanListItem(BaseModel):
    scan_id: UUID
    session_id: UUID
    batch_code: Optional[str]
    breed_code: DuckBreed
    final_class: FertilityClass
    confidence: float
    inference_ms: int
    routing_action: RoutingAction
    scanned_at: datetime

class SessionSummaryResponse(BaseModel):
    session_id: UUID
    batch_code: str
    breed_code: DuckBreed
    stage: CandlingStage
    started_at: datetime
    total_scans: int
    fertile_count: int
    infertile_count: int
    abnormal_count: int


class SessionStatsResponse(BaseModel):
    session_id: UUID
    batch_code: str
    breed_code: DuckBreed
    stage: CandlingStage
    started_at: datetime
    ended_at: Optional[datetime] = None
    total_scans: int
    fertile_count: int
    infertile_count: int
    abnormal_count: int
    avg_inference_ms: float


class HatchioBatchCandlingSummary(BaseModel):
    batch_id: str
    breed: str
    set_date: Optional[datetime] = None
    incubation_day: int = 0
    status: str
    total_scanned: int
    fertile_count: int
    infertile_count: int
    early_dead_count: int
    fertility_rate_pct: float
    scans_by_stage: dict = Field(default_factory=dict)
    last_scanned_at: Optional[datetime] = None


class HatchioEggScanDetail(BaseModel):
    tray_id: str
    egg_position: str
    classification: str
    confidence: float
    scanned_at: datetime


class HatchioBatchDetailsResponse(BaseModel):
    batch_id: str
    breed: str
    total_scanned: int
    scans: List[HatchioEggScanDetail]

# Enable CORS for Web Dashboard connections (React, Vue, Vite, Next.js)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", "http://127.0.0.1:3000",
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:5174", "http://127.0.0.1:5174",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/dashboard", response_class=HTMLResponse, include_in_schema=False)
def dashboard_index():
    return RedirectResponse(url="/dashboard/static/index.html")

@app.get("/dashboard/", response_class=HTMLResponse, include_in_schema=False)
def dashboard_index_slash():
    return RedirectResponse(url="/dashboard/static/index.html")

@app.get("/dashboard/api/summary", tags=["Dashboard"], include_in_schema=False)
def dashboard_summary(db: Session = Depends(get_db)):
    return get_analytics_summary(db=db, _=None)

@app.get("/dashboard/api/sessions", tags=["Dashboard"], include_in_schema=False)
def dashboard_sessions(db: Session = Depends(get_db)):
    return get_sessions(db=db, _=None)

@app.get("/dashboard/api/batches/active", tags=["Dashboard"], include_in_schema=False)
def dashboard_active_batches(db: Session = Depends(get_db)):
    return get_active_batches(status=None, incubator_id=None, db=db, _=None)

@app.get("/dashboard/api/batches/{batch_id}", tags=["Dashboard"], include_in_schema=False)
def dashboard_batch_details(batch_id: str, db: Session = Depends(get_db)):
    return get_hatchio_candling_details(batch_id=batch_id, db=db)

@app.get("/dashboard/api/tables", tags=["Dashboard"], include_in_schema=False)
def dashboard_table_list(db: Session = Depends(get_db)):
    table_names = [table.name for table in Base.metadata.sorted_tables]
    return sorted(table_names)

@app.get("/dashboard/api/tables/{table_name}", tags=["Dashboard"], include_in_schema=False)
def dashboard_table_rows(
    table_name: str,
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    table_names = {table.name for table in Base.metadata.sorted_tables}
    if table_name not in table_names:
        raise HTTPException(status_code=404, detail=f"Table '{table_name}' not found")

    result = db.execute(text(f"SELECT * FROM {table_name} LIMIT :limit"), {"limit": limit})
    rows = [jsonable_encoder(dict(row)) for row in result.mappings().all()]
    columns = list(rows[0].keys()) if rows else []
    return {
        "table": table_name,
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
    }


@app.get("/dashboard/api/sessions/{session_id}/stats", tags=["Dashboard"], include_in_schema=False)
def dashboard_session_stats(session_id: UUID, db: Session = Depends(get_db)):
    return get_session_stats(session_id=session_id, db=db, _=None)


@app.get("/dashboard/api/sessions/{session_id}/scans", tags=["Dashboard"], include_in_schema=False)
def dashboard_session_scans(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return get_session_scans(session_id=session_id, limit=limit, offset=offset, db=db, _=None)

# ==============================================================================
# API ENDPOINTS
# ==============================================================================
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: Optional[str] = Depends(api_key_header)):
    if not API_KEY:
        return None
    if api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key")
    return None


@app.get("/", tags=["Health"])
@app.get("/api/v1/health", tags=["Health"])
def health_check():
    return {"status": "online", "system": "OvaLens Central Backend Server"}

# ------------------------------------------------------------------------------
# 1. INGESTION / SYNC ENDPOINT
# ------------------------------------------------------------------------------
@app.post("/api/v1/scans/sync", status_code=status.HTTP_201_CREATED, tags=["Sync Worker"])
def sync_scan(payload: ScanSyncPayload, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Ingests scan payloads from edge stations into PostgreSQL."""
    try:
        existing_session = db.query(SessionModel).filter(SessionModel.session_id == payload.session_id).first()
        if not existing_session:
            new_session = SessionModel(
                session_id=payload.session_id,
                batch_code=payload.batch_code,
                breed_code=payload.breed_code,
                stage=payload.stage,
                started_at=payload.scanned_at
            )
            db.add(new_session)
            db.flush()

        existing_scan = db.query(ScanModel).filter(ScanModel.scan_id == payload.scan_id).first()
        if existing_scan:
            return {"status": "success", "message": "Scan already synced", "scan_id": payload.scan_id}

        action = payload.routing_action
        if not action:
            action = RoutingAction.ACCEPT if payload.final_class == FertilityClass.FERTILE else RoutingAction.REJECT

        new_scan = ScanModel(
            scan_id=payload.scan_id,
            session_id=payload.session_id,
            breed_code=payload.breed_code,
            final_class=payload.final_class,
            confidence=payload.confidence,
            inference_ms=payload.inference_ms,
            routing_action=action,
            image_url=payload.image_url,
            scanned_at=payload.scanned_at
        )
        db.add(new_scan)
        db.flush()

        for det in payload.detections:
            if len(det.bbox) == 4:
                new_det = DetectionModel(
                    scan_id=payload.scan_id,
                    class_label=det.class_label,
                    confidence=det.confidence,
                    bbox_x_center=det.bbox[0],
                    bbox_y_center=det.bbox[1],
                    bbox_width=det.bbox[2],
                    bbox_height=det.bbox[3]
                )
                db.add(new_det)

        db.commit()
        return {"status": "success", "scan_id": payload.scan_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist scan record: {str(e)}"
        )

@app.post("/api/v1/scans/upload-image", status_code=status.HTTP_201_CREATED, tags=["Sync Worker"])
def upload_scan_image(scan_id: UUID = Form(...), file: UploadFile = File(...), _: None = Depends(verify_api_key)):
    """Mock stub endpoint for accepting and saving uploaded scan images."""
    return {"status": "success", "message": f"Image received for {scan_id}"}

# ------------------------------------------------------------------------------
# 2. DASHBOARD ANALYTICS SUMMARY
# ------------------------------------------------------------------------------
@app.get("/api/v1/analytics/summary", tags=["Dashboard Analytics"])
def get_analytics_summary(db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Computes hatchery KPIs: Fertility rate, breed distributions, and average performance."""
    total_scans = db.query(func.count(ScanModel.scan_id)).scalar() or 0

    class_counts = (
        db.query(ScanModel.final_class, func.count(ScanModel.scan_id))
        .group_by(ScanModel.final_class)
        .all()
    )
    class_map = {cls.value: count for cls, count in class_counts}

    fertile_count = class_map.get("FERTILE", 0)
    infertile_count = class_map.get("INFERTILE", 0)
    abnormal_count = class_map.get("ABNORMAL", 0)

    fertility_rate = (fertile_count / total_scans * 100) if total_scans > 0 else 0.0
    avg_inference_ms = db.query(func.avg(ScanModel.inference_ms)).scalar() or 0.0

    breed_counts = (
        db.query(ScanModel.breed_code, func.count(ScanModel.scan_id))
        .group_by(ScanModel.breed_code)
        .all()
    )
    breed_map = {breed.value: count for breed, count in breed_counts}

    return {
        "metrics": {
            "total_eggs_scanned": total_scans,
            "overall_fertility_rate_pct": round(fertility_rate, 2),
            "avg_inference_speed_ms": round(float(avg_inference_ms), 1),
        },
        "classification_breakdown": {
            "fertile": fertile_count,
            "infertile": infertile_count,
            "abnormal": abnormal_count,
        },
        "breed_breakdown": {
            "kayumanggi": breed_map.get("KAYUMANGGI", 0),
            "itim": breed_map.get("ITIM", 0),
            "khaki": breed_map.get("KHAKI", 0),
        }
    }

# ------------------------------------------------------------------------------
# 3. LIST SESSIONS / BATCHES
# ------------------------------------------------------------------------------
@app.get("/api/v1/sessions", response_model=List[SessionSummaryResponse], tags=["Batches & Sessions"])
def get_sessions(db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Lists all incubation sessions with fertility statistics per batch."""
    sessions = (
        db.query(SessionModel)
        .options(selectinload(SessionModel.scans))
        .order_by(desc(SessionModel.started_at))
        .all()
    )
    results = []

    for s in sessions:
        scans = s.scans
        total = len(scans)
        fertile = sum(1 for sc in scans if sc.final_class == FertilityClass.FERTILE)
        infertile = sum(1 for sc in scans if sc.final_class == FertilityClass.INFERTILE)
        abnormal = sum(1 for sc in scans if sc.final_class == FertilityClass.ABNORMAL)

        results.append(
            SessionSummaryResponse(
                session_id=s.session_id,
                batch_code=s.batch_code,
                breed_code=s.breed_code,
                stage=s.stage,
                started_at=s.started_at,
                total_scans=total,
                fertile_count=fertile,
                infertile_count=infertile,
                abnormal_count=abnormal
            )
        )
    return results

@app.post("/api/v1/sessions", status_code=status.HTTP_201_CREATED, tags=["Batches & Sessions"])
def create_session(payload: SessionCreatePayload, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    try:
        new_session = SessionModel(
            session_id=payload.session_id,
            batch_code=payload.batch_code,
            breed_code=payload.breed_code,
            stage=payload.stage,
            started_at=datetime.now(timezone.utc)
        )
        db.add(new_session)
        db.commit()
        return {"status": "success", "session_id": payload.session_id}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/api/v1/sessions/{session_id}", tags=["Batches & Sessions"])
def end_session(session_id: UUID, payload: SessionEndPayload, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.ended_at = payload.ended_at
    db.commit()
    return {"status": "success"}


@app.get("/api/v1/sessions/{session_id}/stats", response_model=SessionStatsResponse, tags=["Batches & Sessions"])
def get_session_stats(session_id: UUID, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    counts = (
        db.query(
            func.count(ScanModel.scan_id).label("total_scans"),
            func.sum(case((ScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)).label("fertile_count"),
            func.sum(case((ScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)).label("infertile_count"),
            func.sum(case((ScanModel.final_class == FertilityClass.ABNORMAL, 1), else_=0)).label("abnormal_count"),
            func.avg(ScanModel.inference_ms).label("avg_inference_ms"),
        )
        .filter(ScanModel.session_id == session_id)
        .one()
    )

    return SessionStatsResponse(
        session_id=session.session_id,
        batch_code=session.batch_code,
        breed_code=session.breed_code,
        stage=session.stage,
        started_at=session.started_at,
        ended_at=session.ended_at,
        total_scans=counts.total_scans or 0,
        fertile_count=counts.fertile_count or 0,
        infertile_count=counts.infertile_count or 0,
        abnormal_count=counts.abnormal_count or 0,
        avg_inference_ms=float(counts.avg_inference_ms or 0.0),
    )


@app.get("/api/v1/sessions/{session_id}/scans", response_model=List[ScanListItem], tags=["Batches & Sessions"])
def get_session_scans(
    session_id: UUID,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """Returns paginated scan records for a given session (most recent first)."""
    query = db.query(ScanModel, SessionModel.batch_code).join(
        SessionModel, ScanModel.session_id == SessionModel.session_id
    ).filter(SessionModel.session_id == session_id)

    rows = query.order_by(desc(ScanModel.scanned_at)).offset(offset).limit(limit).all()

    return [
        ScanListItem(
            scan_id=scan.scan_id,
            session_id=scan.session_id,
            batch_code=batch_code,
            breed_code=scan.breed_code,
            final_class=scan.final_class,
            confidence=float(scan.confidence),
            inference_ms=scan.inference_ms,
            routing_action=scan.routing_action,
            scanned_at=scan.scanned_at,
        )
        for scan, batch_code in rows
    ]

# ------------------------------------------------------------------------------
# 4. ACTIVE INCUBATION BATCHES  (Hatchio ↔ OvaLens Integration)
# ------------------------------------------------------------------------------
@app.get(
    "/api/v1/batches/active",
    response_model=List[ActiveBatchResponse],
    tags=["Incubation Batches"],
    summary="Fetch active incubation batches",
)
def get_active_batches(
    status: Optional[BatchStatus] = Query(
        None, description="Filter by batch status, e.g. CANDLING_DUE or INCUBATING"
    ),
    incubator_id: Optional[str] = Query(
        None, description="Filter by physical incubator unit ID"
    ),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Returns all *non-completed* incubation batches so edge devices (OvaLens)
    can display them to operators for candling selection.

    **Example response:**
    ```json
    [
      {
        "batch_id": "BATCH-2026-0728",
        "breed": "Kayumanggi",
        "set_date": "2026-07-18T06:00:00Z",
        "incubation_day": 10,
        "status": "CANDLING_DUE"
      }
    ]
    ```
    """
    # Best-effort sync from Hatchio Firebase database
    try:
        from services.firebase_writer import get_active_batch
        remote_batch_id, remote_batch_data = get_active_batch()
        if remote_batch_id and remote_batch_data:
            existing = db.query(BatchModel).filter(BatchModel.batch_id == remote_batch_id).first()
            
            # Extract breed from trays dict if available, fallback to species/Duck
            breed = "Kayumanggi"
            trays = remote_batch_data.get("trays")
            if isinstance(trays, dict) and len(trays) > 0:
                first_tray = next(iter(trays.values()))
                if isinstance(first_tray, dict) and first_tray.get("breed"):
                    breed = first_tray.get("breed")
            elif remote_batch_data.get("species"):
                breed = remote_batch_data.get("species")

            set_date_str = remote_batch_data.get("setDate")
            parsed_set_date = datetime.now(timezone.utc)
            if set_date_str:
                try:
                    if len(set_date_str) == 10:
                        parsed_set_date = datetime.strptime(set_date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
                    else:
                        parsed_set_date = datetime.fromisoformat(set_date_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            now = datetime.now(timezone.utc)
            day_diff = (now - parsed_set_date).days if parsed_set_date else 0

            if not existing:
                new_batch = BatchModel(
                    batch_id=remote_batch_id,
                    breed=breed,
                    set_date=parsed_set_date,
                    incubation_day=max(0, day_diff),
                    status=BatchStatus.INCUBATING
                )
                db.add(new_batch)
                db.commit()
            else:
                # Update incubation day and breed if changed
                existing.incubation_day = max(0, day_diff)
                existing.breed = breed
                db.commit()
    except Exception as e:
        # Ignore remote sync errors if Hatchio network host is unreachable
        pass

    query = db.query(BatchModel).filter(BatchModel.status != BatchStatus.COMPLETED)

    if status:
        query = query.filter(BatchModel.status == status)
    if incubator_id:
        query = query.filter(BatchModel.incubator_id == incubator_id)

    batches = query.order_by(BatchModel.set_date.desc()).all()
    return batches


# ------------------------------------------------------------------------------
# 5. CANDLING SCAN INGESTION  (OvaLens Edge → Central API)
# ------------------------------------------------------------------------------
@app.post(
    "/api/v1/candling/scans",
    status_code=status.HTTP_201_CREATED,
    response_model=CandlingScanSummaryResponse,
    tags=["Candling Scans"],
    summary="Record candling classification results from OvaLens",
)
def create_candling_scans(
    payload: CandlingScanPayload,
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key),
):
    """
    Receives candling classification results from the OvaLens Edge App and
    persists them as individual scan records tied to the given batch.

    **Validation:**
    - `batch_id` must reference an existing, non-completed batch.
    - Each scan item must include `tray_id`, `egg_position`, `classification`,
      and `confidence` (0.0–1.0).

    **Example request body:**
    ```json
    {
      "batch_id": "BATCH-2026-0728",
      "scanned_at": "2026-07-28T14:30:00Z",
      "operator_id": "OP-001",
      "scans": [
        {"tray_id": "TRAY-A", "egg_position": "A1", "classification": "fertile", "confidence": 0.97},
        {"tray_id": "TRAY-A", "egg_position": "A2", "classification": "infertile", "confidence": 0.85},
        {"tray_id": "TRAY-A", "egg_position": "A3", "classification": "early_dead", "confidence": 0.72}
      ]
    }
    ```
    """
    # --- Validate batch exists ---------------------------------------------------
    batch = db.query(BatchModel).filter(BatchModel.batch_id == payload.batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Batch '{payload.batch_id}' does not exist. "
                   f"Please provide a valid batch_id.",
        )

    # --- Bulk-insert candling scan records ---------------------------------------
    try:
        for item in payload.scans:
            record = CandlingScanModel(
                batch_id=payload.batch_id,
                tray_id=item.tray_id,
                egg_position=item.egg_position,
                classification=item.classification,
                confidence=item.confidence,
                operator_id=payload.operator_id,
                scanned_at=payload.scanned_at,
            )
            db.add(record)

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist candling scans: {str(e)}",
        )

    # --- Best-effort external Hatchio dashboard sync ---------------------------
    external_sync_status = "not_attempted"
    external_sync_record_id = None
    try:
        from services.firebase_writer import push_candling_from_items

        remote_record_id = push_candling_from_items(
            batch_id=payload.batch_id,
            day=batch.incubation_day,
            items=[item.model_dump() for item in payload.scans],
        )
        if remote_record_id == "SKIPPED_DUPLICATE_DAY":
            external_sync_status = "duplicate_skipped"
        else:
            external_sync_status = "sent"
            external_sync_record_id = remote_record_id
    except Exception:
        # Do not fail the local ingest endpoint if the external dashboard host
        # is missing or temporarily unavailable.
        external_sync_status = "unavailable"

    # --- Build classification summary -------------------------------------------
    summary: dict[str, int] = {}
    for item in payload.scans:
        key = item.classification.lower()
        summary[key] = summary.get(key, 0) + 1

    return CandlingScanSummaryResponse(
        status="success",
        batch_id=payload.batch_id,
        total_scans_recorded=len(payload.scans),
        classification_summary=summary,
        scanned_at=payload.scanned_at,
        external_sync_status=external_sync_status,
        external_sync_record_id=external_sync_record_id,
    )


# ------------------------------------------------------------------------------
# 6. FILTERED SCANS LIST (PAGINATED)
# ------------------------------------------------------------------------------
@app.get("/api/v1/scans", response_model=List[ScanListItem], tags=["Scan Records"])
def get_scans(
    breed: Optional[DuckBreed] = None,
    fertility: Optional[FertilityClass] = None,
    max_confidence: Optional[float] = Query(None, description="Useful for flagging low-confidence predictions for human review"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: None = Depends(verify_api_key)
):
    """Retrieves paginated scan records with flexible filters."""
    query = db.query(ScanModel, SessionModel.batch_code).join(
        SessionModel, ScanModel.session_id == SessionModel.session_id
    )

    if breed:
        query = query.filter(ScanModel.breed_code == breed)
    if fertility:
        query = query.filter(ScanModel.final_class == fertility)
    if max_confidence is not None:
        query = query.filter(ScanModel.confidence <= max_confidence)

    rows = query.order_by(desc(ScanModel.scanned_at)).offset(offset).limit(limit).all()

    return [
        ScanListItem(
            scan_id=scan.scan_id,
            session_id=scan.session_id,
            batch_code=batch_code,
            breed_code=scan.breed_code,
            final_class=scan.final_class,
            confidence=float(scan.confidence),
            inference_ms=scan.inference_ms,
            routing_action=scan.routing_action,
            scanned_at=scan.scanned_at
        )
        for scan, batch_code in rows
    ]

# ------------------------------------------------------------------------------
# 7. DETAILED SINGLE SCAN WITH BOUNDING BOXES
# ------------------------------------------------------------------------------
@app.get("/api/v1/scans/{scan_id}", response_model=ScanDetailResponse, tags=["Scan Records"])
def get_scan_by_id(scan_id: UUID, db: Session = Depends(get_db), _: None = Depends(verify_api_key)):
    """Retrieves full details for a single scan including YOLO bounding box coordinates."""
    scan = db.query(ScanModel).filter(ScanModel.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan record not found")

    detections = [
        DetectionResponse(
            detection_id=d.detection_id,
            class_label=d.class_label,
            confidence=float(d.confidence),
            bbox=[
                float(d.bbox_x_center),
                float(d.bbox_y_center),
                float(d.bbox_width),
                float(d.bbox_height)
            ]
        )
        for d in scan.detections
    ]

    return ScanDetailResponse(
        scan_id=scan.scan_id,
        session_id=scan.session_id,
        breed_code=scan.breed_code,
        final_class=scan.final_class,
        confidence=float(scan.confidence),
        inference_ms=scan.inference_ms,
        routing_action=scan.routing_action,
        image_url=scan.image_url,
        scanned_at=scan.scanned_at,
        synced_at=scan.synced_at,
        detections=detections
    )


# ------------------------------------------------------------------------------
# 8. HATCHIO INTEGRATION ENDPOINTS (Fetch batch candling, fertility & egg counts)
# ------------------------------------------------------------------------------
@app.get(
    "/api/v1/hatchio/batches/candling-summary",
    response_model=List[HatchioBatchCandlingSummary],
    tags=["Hatchio Integration"],
    summary="Fetch candling summary, fertility stats, and egg counts for Hatchio Dashboard",
)
def get_hatchio_candling_summary(db: Session = Depends(get_db)):
    """
    Returns aggregated candling data, fertility counts, and egg metrics per batch
    specifically formatted for ingestion by Hatchio Dashboard.
    """
    batches = db.query(BatchModel).all()
    results = []

    for b in batches:
        candling_scans = (
            db.query(CandlingScanModel)
            .filter(CandlingScanModel.batch_id == b.batch_id)
            .all()
        )

        fertile = sum(1 for c in candling_scans if c.classification.lower() == "fertile")
        infertile = sum(1 for c in candling_scans if c.classification.lower() == "infertile")
        early_dead = sum(
            1 for c in candling_scans if c.classification.lower() in ["early_dead", "abnormal"]
        )
        total = len(candling_scans)

        # Fallback to SessionModel scans if no CandlingScanModel records exist for batch_id
        if total == 0:
            session_scans = (
                db.query(ScanModel)
                .join(SessionModel, ScanModel.session_id == SessionModel.session_id)
                .filter(SessionModel.batch_code == b.batch_id)
                .all()
            )
            total = len(session_scans)
            fertile = sum(1 for sc in session_scans if sc.final_class == FertilityClass.FERTILE)
            infertile = sum(1 for sc in session_scans if sc.final_class == FertilityClass.INFERTILE)
            early_dead = sum(1 for sc in session_scans if sc.final_class == FertilityClass.ABNORMAL)

        fertility_rate = (fertile / total * 100.0) if total > 0 else 0.0

        last_scanned = None
        if candling_scans:
            last_scanned = max(c.scanned_at for c in candling_scans)

        stage_breakdown = {
            "DAY_10": sum(1 for c in candling_scans if getattr(c, "day", None) == 10),
            "DAY_18": sum(1 for c in candling_scans if getattr(c, "day", None) == 18),
            "DAY_25": sum(1 for c in candling_scans if getattr(c, "day", None) == 25),
        }

        results.append(
            HatchioBatchCandlingSummary(
                batch_id=b.batch_id,
                breed=b.breed,
                set_date=b.set_date,
                incubation_day=b.incubation_day,
                status=b.status.value if hasattr(b.status, "value") else str(b.status),
                total_scanned=total,
                fertile_count=fertile,
                infertile_count=infertile,
                early_dead_count=early_dead,
                fertility_rate_pct=round(fertility_rate, 2),
                scans_by_stage=stage_breakdown,
                last_scanned_at=last_scanned,
            )
        )

    return results


@app.get(
    "/api/v1/hatchio/batches/{batch_id}/candling-details",
    response_model=HatchioBatchDetailsResponse,
    tags=["Hatchio Integration"],
    summary="Fetch egg-level candling scan details for a specific batch",
)
def get_hatchio_candling_details(batch_id: str, db: Session = Depends(get_db)):
    batch = db.query(BatchModel).filter(BatchModel.batch_id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail=f"Batch '{batch_id}' not found")

    scans = (
        db.query(CandlingScanModel)
        .filter(CandlingScanModel.batch_id == batch_id)
        .order_by(CandlingScanModel.scanned_at.asc())
        .all()
    )

    items = [
        HatchioEggScanDetail(
            tray_id=s.tray_id,
            egg_position=s.egg_position,
            classification=s.classification,
            confidence=float(s.confidence),
            scanned_at=s.scanned_at,
        )
        for s in scans
    ]

    return HatchioBatchDetailsResponse(
        batch_id=batch.batch_id,
        breed=batch.breed,
        total_scanned=len(items),
        scans=items,
    )


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)