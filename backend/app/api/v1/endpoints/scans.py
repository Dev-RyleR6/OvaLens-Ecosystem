import os
import shutil
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.config import settings
from app.core.database import get_db
from app.models.scan import EggScanModel, FertilityClass
from app.schemas.scan import ScanSyncPayload, ScanSyncResponse, ScanListItem, ScanDetailResponse, ScanOverridePayload
from app.services.scan_service import ScanService
from app.api.deps import verify_api_key

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
    scan = db.query(EggScanModel).filter(EggScanModel.scan_id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scan '{scan_id}' not found.")

    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    filename = f"{scan_id}.jpg"
    file_path = os.path.join(settings.STORAGE_DIR, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    image_url = f"/storage/{filename}"
    scan.image_url = image_url
    scan.thumbnail_url = image_url
    db.commit()

    return {"status": "success", "scan_id": scan_id, "image_url": image_url}


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
    db: Session = Depends(get_db)
):
    return ScanService.override_scan(db, scan_id, payload.final_class)
