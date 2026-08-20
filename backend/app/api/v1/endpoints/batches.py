from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.batch import DuckBreed, BatchStatus
from app.models.user import UserModel
from app.schemas.batch import BatchCreate, BatchUpdate, BatchResponse, BatchSummaryResponse, AdvanceStagePayload
from app.services.batch_service import BatchService
from app.api.deps import get_current_user, require_manager_or_admin

router = APIRouter(prefix="/batches", tags=["Incubation Batches"])


@router.get("", response_model=List[BatchResponse], summary="List all incubation batches")
def list_batches(
    status: Optional[BatchStatus] = None,
    breed: Optional[DuckBreed] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    return BatchService.list_batches(db, status=status, breed=breed, limit=limit, offset=offset)


@router.get("/active", response_model=List[BatchResponse], summary="List active incubation batches for Edge selection")
def list_active_batches(db: Session = Depends(get_db)):
    return BatchService.list_batches(db, status=BatchStatus.INCUBATING)


@router.post("", response_model=BatchResponse, summary="Create a new incubation batch")
def create_batch(
    payload: BatchCreate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    return BatchService.create_batch(db, payload, user_id=current_user.user_id)


@router.get("/{batch_id}", response_model=BatchResponse, summary="Get batch details by ID")
def get_batch(batch_id: str, db: Session = Depends(get_db)):
    return BatchService.get_batch(db, batch_id)


@router.put("/{batch_id}", response_model=BatchResponse, summary="Update batch status or hatch counts")
def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    return BatchService.update_batch(db, batch_id, payload)


@router.post("/{batch_id}/advance-stage", response_model=BatchResponse, summary="Advance batch incubation milestone stage")
def advance_batch_stage(
    batch_id: str,
    payload: AdvanceStagePayload,
    db: Session = Depends(get_db)
):
    return BatchService.advance_stage(db, batch_id, payload.stage)


@router.get("/{batch_id}/summary", response_model=BatchSummaryResponse, summary="Get comprehensive batch metrics summary")
def get_batch_summary(batch_id: str, db: Session = Depends(get_db)):
    return BatchService.get_batch_summary(db, batch_id)
