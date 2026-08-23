from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.batch import DuckBreed, BatchStatus
from app.models.user import UserModel
from app.models.audit import AuditLogModel
from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchResponse, BatchSummaryResponse, AdvanceStagePayload,
    BatchAnalyticsResponse, FinalizeHatchPayload, MilestoneCheckResponse, BatchForecastResponse
)
from app.services.batch_service import BatchService
from app.services.forecast_service import ForecastService
from app.api.deps import get_current_user, require_manager_or_admin

router = APIRouter(prefix="/batches", tags=["Incubation Batches"])


@router.get("", response_model=List[BatchSummaryResponse], summary="List all incubation batches with metrics")
def list_batches(
    status: Optional[BatchStatus] = None,
    breed: Optional[DuckBreed] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    batches = BatchService.list_batches(db, status=status, breed=breed, limit=limit, offset=offset)
    return [BatchService.get_batch_summary(db, b.batch_id) for b in batches]


@router.get("/active", response_model=List[BatchResponse], summary="List active incubation batches for Edge selection")
def list_active_batches(db: Session = Depends(get_db)):
    return BatchService.list_batches(db, status=BatchStatus.INCUBATING)


@router.post("/check-milestones", response_model=MilestoneCheckResponse, summary="Evaluate elapsed incubation days and flag due candling/transfer milestones")
def check_milestones(db: Session = Depends(get_db)):
    return BatchService.check_due_milestones(db)


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


@router.get("/{batch_id}/analytics", response_model=BatchAnalyticsResponse, summary="Get deep batch analytics and embryo mortality breakdown")
def get_batch_analytics(batch_id: str, db: Session = Depends(get_db)):
    return BatchService.get_batch_deep_analytics(db, batch_id)


@router.get("/{batch_id}/forecast", response_model=BatchForecastResponse, summary="Predict Day 28 hatch yield, revenue forecast, and biological anomalies")
def get_batch_forecast(batch_id: str, db: Session = Depends(get_db)):
    return ForecastService.get_batch_forecast(db, batch_id)


@router.put("/{batch_id}", response_model=BatchResponse, summary="Update batch status or hatch counts")
def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    batch = BatchService.update_batch(db, batch_id, payload)
    
    # Audit log
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="BATCH_UPDATED",
        entity_type="BATCH",
        entity_id=batch_id,
        details={"updated_fields": list(payload.model_dump(exclude_unset=True).keys()), "updated_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    return batch


@router.post("/{batch_id}/advance-stage", response_model=BatchResponse, summary="Advance batch incubation milestone stage")
def advance_batch_stage(
    batch_id: str,
    payload: AdvanceStagePayload,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    batch = BatchService.advance_stage(db, batch_id, payload.stage)
    
    # Audit log
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="STAGE_ADVANCED",
        entity_type="BATCH",
        entity_id=batch_id,
        details={"new_stage": payload.stage, "advanced_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    return batch


@router.post("/{batch_id}/finalize-hatch", response_model=BatchResponse, summary="Finalize Day 28 hatch trial and record duckling count")
def finalize_hatch(
    batch_id: str,
    payload: FinalizeHatchPayload,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    batch = BatchService.finalize_hatch(db, batch_id, payload)
    
    # Audit log
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="BATCH_HATCH_FINALIZED",
        entity_type="BATCH",
        entity_id=batch_id,
        details={"hatched_count": payload.hatched_count, "unhatched_count": batch.unhatched_count, "finalized_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    return batch


@router.get("/{batch_id}/summary", response_model=BatchSummaryResponse, summary="Get comprehensive batch metrics summary")
def get_batch_summary(batch_id: str, db: Session = Depends(get_db)):
    return BatchService.get_batch_summary(db, batch_id)


@router.delete("/{batch_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete or archive an incubation batch")
def delete_batch(
    batch_id: str,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    BatchService.delete_batch(db, batch_id)
    
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="BATCH_DELETED",
        entity_type="BATCH",
        entity_id=batch_id,
        details={"deleted_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    return None

