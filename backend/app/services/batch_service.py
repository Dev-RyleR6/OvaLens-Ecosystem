from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.models.batch import BatchModel, BatchStage, BatchStatus, DuckBreed
from app.models.session import CandlingSessionModel
from app.schemas.batch import BatchCreate, BatchUpdate, BatchSummaryResponse
from app.core.exceptions import DuplicateEntityException, EntityNotFoundException, InvalidBatchStateTransitionException


class BatchService:
    @staticmethod
    def create_batch(db: Session, payload: BatchCreate, user_id: Optional[UUID] = None) -> BatchModel:
        # Check uniqueness of batch_code
        existing = db.query(BatchModel).filter(BatchModel.batch_code == payload.batch_code).first()
        if existing:
            raise DuplicateEntityException(f"Batch with code '{payload.batch_code}' already exists.")

        # Duck egg incubation is precisely 28 days
        target_hatch = payload.set_date + timedelta(days=28)
        batch_id = payload.batch_code.upper().replace(" ", "-")

        batch = BatchModel(
            batch_id=batch_id,
            batch_code=payload.batch_code,
            breed=payload.breed,
            incubator_id=payload.incubator_id,
            initial_egg_count=payload.initial_egg_count,
            set_date=payload.set_date,
            target_hatch_date=target_hatch,
            current_stage=BatchStage.SETTING,
            status=BatchStatus.INCUBATING,
            notes=payload.notes,
            created_by=user_id
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def get_batch(db: Session, batch_id: str) -> BatchModel:
        batch = db.query(BatchModel).filter(BatchModel.batch_id == batch_id).first()
        if not batch:
            raise EntityNotFoundException(f"Batch '{batch_id}' not found.")
        return batch

    @staticmethod
    def list_batches(
        db: Session,
        status: Optional[BatchStatus] = None,
        breed: Optional[DuckBreed] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[BatchModel]:
        query = db.query(BatchModel)
        if status:
            query = query.filter(BatchModel.status == status)
        if breed:
            query = query.filter(BatchModel.breed == breed)
        return query.order_by(desc(BatchModel.set_date)).offset(offset).limit(limit).all()

    @staticmethod
    def update_batch(db: Session, batch_id: str, payload: BatchUpdate) -> BatchModel:
        batch = BatchService.get_batch(db, batch_id)
        if payload.incubator_id is not None:
            batch.incubator_id = payload.incubator_id
        if payload.notes is not None:
            batch.notes = payload.notes
        if payload.status is not None:
            batch.status = payload.status
        if payload.hatched_count is not None:
            batch.hatched_count = payload.hatched_count
            if batch.hatched_count > batch.initial_egg_count:
                raise InvalidBatchStateTransitionException("Hatched count cannot exceed initial egg count.")
        if payload.unhatched_count is not None:
            batch.unhatched_count = payload.unhatched_count

        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def advance_stage(db: Session, batch_id: str, stage: BatchStage) -> BatchModel:
        batch = BatchService.get_batch(db, batch_id)
        batch.current_stage = stage
        if stage in (BatchStage.HATCHED, BatchStage.COMPLETED):
            batch.status = BatchStatus.COMPLETED
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def get_batch_summary(db: Session, batch_id: str) -> BatchSummaryResponse:
        batch = BatchService.get_batch(db, batch_id)

        # Aggregate metrics across all sessions
        totals = db.query(
            func.coalesce(func.sum(CandlingSessionModel.total_scanned), 0).label("scanned"),
            func.coalesce(func.sum(CandlingSessionModel.fertile_count), 0).label("fertile"),
            func.coalesce(func.sum(CandlingSessionModel.infertile_count), 0).label("infertile"),
            func.coalesce(func.sum(CandlingSessionModel.abnormal_count), 0).label("abnormal")
        ).filter(CandlingSessionModel.batch_id == batch_id).first()

        total_scanned = totals.scanned or 0
        fertile = totals.fertile or 0
        infertile = totals.infertile or 0
        abnormal = totals.abnormal or 0

        fertility_rate = (fertile / total_scanned * 100.0) if total_scanned > 0 else 0.0
        hatchability_rate = (batch.hatched_count / batch.initial_egg_count * 100.0) if batch.initial_egg_count > 0 else 0.0

        return BatchSummaryResponse(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            breed=batch.breed,
            incubator_id=batch.incubator_id,
            initial_egg_count=batch.initial_egg_count,
            set_date=batch.set_date,
            target_hatch_date=batch.target_hatch_date,
            current_stage=batch.current_stage,
            status=batch.status,
            total_scanned=total_scanned,
            fertile_count=fertile,
            infertile_count=infertile,
            abnormal_count=abnormal,
            fertility_rate=round(fertility_rate, 2),
            hatchability_rate=round(hatchability_rate, 2)
        )
