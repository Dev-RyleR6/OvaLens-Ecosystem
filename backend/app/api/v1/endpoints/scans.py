from typing import List, Optional, Literal
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Request
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, cast, String
from app.core.config import settings
from app.core.database import get_db
from app.models.scan import EggScanModel, FertilityClass
from app.models.user import UserModel
from app.schemas.scan import ScanSyncPayload, ScanSyncResponse, ScanListItem, ScanDetailResponse, ScanOverridePayload, ScanPage
from app.services.scan_service import ScanService
from app.services.scan_images import store_scan_image
from app.services.scan_metrics import review_condition
from app.api.deps import verify_api_key, get_current_user

router = APIRouter(prefix="/scans", tags=["Egg Scans & Ingestion"])


@router.post("/sync", response_model=ScanSyncResponse, summary="Idempotent bulk scan ingestion from Edge machine")
def sync_scans(
    payload: ScanSyncPayload,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    return ScanService.sync_scans(db, payload)


@router.post("/upload-image", summary="Upload high-resolution candling scan photo")
def upload_scan_image(
    scan_id: UUID = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    scan = db.query(EggScanModel).filter(EggScanModel.scan_id == scan_id).with_for_update().first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scan '{scan_id}' not found.")

    acknowledgement = store_scan_image(scan_id, file, settings.STORAGE_DIR, settings.MAX_SCAN_IMAGE_BYTES)
    scan.image_url = acknowledgement["image_url"]
    scan.thumbnail_url = acknowledgement["image_url"]
    db.commit()

    return acknowledgement


@router.get("", response_model=List[ScanListItem], summary="Search and filter egg scans")
def list_scans(
    batch_id: Optional[str] = None,
    session_id: Optional[UUID] = None,
    final_class: Optional[FertilityClass] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(EggScanModel)
    if batch_id:
        query = query.filter(EggScanModel.batch_id == batch_id)
    if session_id:
        query = query.filter(EggScanModel.session_id == session_id)
    if final_class:
        query = query.filter(EggScanModel.final_class == final_class)
    return query.order_by(desc(EggScanModel.scanned_at)).offset(offset).limit(limit).all()


@router.get("/search", response_model=ScanPage, summary="Paginated scan history with search and confidence filters")
def search_scans(
    batch_id: Optional[str] = None,
    final_class: Optional[FertilityClass] = None,
    confidence: Literal["ALL", "HIGH", "MID", "LOW", "REVIEW"] = "ALL",
    q: str = Query("", max_length=200),
    sort: Literal["sequence_number", "confidence", "inference_ms", "scanned_at"] = "scanned_at",
    order: Literal["asc", "desc"] = "desc",
    limit: int = Query(20, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    query = db.query(EggScanModel)
    if batch_id:
        query = query.filter(EggScanModel.batch_id == batch_id)
    if final_class:
        query = query.filter(EggScanModel.final_class == final_class)
    if confidence == "HIGH":
        query = query.filter(EggScanModel.confidence >= 0.90)
    elif confidence == "MID":
        query = query.filter(EggScanModel.confidence >= 0.75, EggScanModel.confidence < 0.90)
    elif confidence == "LOW":
        query = query.filter(EggScanModel.confidence < 0.75)
    elif confidence == "REVIEW":
        query = query.filter(review_condition())
    if q.strip():
        # Treat user search text literally, including SQL LIKE wildcards.
        pattern = "%" + q.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        query = query.filter(or_(
            cast(EggScanModel.scan_id, String).ilike(pattern, escape="\\"),
            EggScanModel.batch_id.ilike(pattern, escape="\\"),
            cast(EggScanModel.sequence_number, String).ilike(pattern, escape="\\"),
        ))
    total = query.count()
    column = getattr(EggScanModel, sort)
    ordering = column.asc() if order == "asc" else column.desc()
    items = query.order_by(ordering, EggScanModel.scan_id.asc()).offset(offset).limit(limit).all()
    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/{scan_id}", response_model=ScanDetailResponse, summary="Get full scan record with bounding boxes")
def get_scan(scan_id: UUID, db: Session = Depends(get_db)):
    scan = db.query(EggScanModel).filter(EggScanModel.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scan '{scan_id}' not found.")
    return scan


@router.patch("/{scan_id}/override", response_model=ScanDetailResponse, summary="Operator Human-in-the-Loop classification override")
def override_scan(
    scan_id: UUID,
    payload: ScanOverridePayload,
    request: Request,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else "127.0.0.1"
    return ScanService.override_scan(
        db=db,
        scan_id=scan_id,
        final_class=payload.final_class,
        reason=payload.reason,
        user_id=current_user.user_id,
        ip_address=client_ip,
    )
