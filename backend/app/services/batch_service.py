from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from sqlalchemy.dialects.postgresql import insert

from app.models.batch import BatchModel, BatchStage, BatchStatus, DuckBreed
from app.models.session import CandlingSessionModel, CandlingStage
from app.models.scan import EggScanModel, FertilityClass
from app.models.settings import HatcherySettingsModel
from app.models.audit import AuditLogModel
from app.services.scan_metrics import scan_totals
from app.schemas.batch import (
    BatchCreate, BatchUpdate, BatchSummaryResponse,
    BatchAnalyticsResponse, SessionSummaryItem, MilestoneCheckResponse, FinalizeHatchPayload
)
from app.core.exceptions import DuplicateEntityException, EntityNotFoundException, InvalidBatchStateTransitionException


class BatchService:
    @staticmethod
    def register_edge_batch(db: Session, payload) -> BatchModel:
        """Create once by permanent Edge ID; conflicting retries never overwrite inventory."""
        values = payload.model_dump(exclude={"device_id", "operator_name"})
        values.update(target_hatch_date=payload.set_date + timedelta(days=28),
                      current_stage=BatchStage.SETTING, status=BatchStatus.INCUBATING)
        inserted = db.execute(insert(BatchModel).values(**values).on_conflict_do_nothing()
                              .returning(BatchModel.batch_id)).scalar_one_or_none()
        batch = db.get(BatchModel, payload.batch_id)
        matches = batch is not None and all(getattr(batch, key) == getattr(payload, key)
            for key in ("batch_code", "breed", "incubator_id", "initial_egg_count", "set_date", "notes"))
        if not matches:
            db.rollback()
            raise DuplicateEntityException("Batch ID or code already exists with different details; saved Edge data must be reviewed.")
        if inserted:
            db.add(AuditLogModel(action="BATCH_CREATED", entity_type="BATCH", entity_id=batch.batch_id,
                details={"source": "EDGE", "device_id": payload.device_id, "operator_name": payload.operator_name}))
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def _compute_milestone(set_date: datetime, current_stage: BatchStage) -> Tuple[int, Optional[str]]:
        now = datetime.now(timezone.utc)
        if set_date.tzinfo is None:
            set_date = set_date.replace(tzinfo=timezone.utc)
        elapsed = max(0, (now - set_date).days)
        
        alert = None
        if current_stage == BatchStage.SETTING and elapsed >= 10:
            alert = "CANDLING DUE: Day 10 Embryo Viability & Penoy Salvage"
        elif elapsed >= 28 and current_stage not in (BatchStage.HATCHED, BatchStage.COMPLETED):
            alert = "HATCH DUE: Day 28 Final Hatch Record Pending"

        return elapsed, alert

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
        return query.order_by(desc(BatchModel.set_date), BatchModel.batch_id).offset(offset).limit(limit).all()

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
        else:
            # Revert from CANDLING_DUE back to INCUBATING once stage advanced
            batch.status = BatchStatus.INCUBATING
        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def check_due_milestones(db: Session) -> MilestoneCheckResponse:
        active_batches = db.query(BatchModel).filter(
            BatchModel.status.in_([BatchStatus.INCUBATING, BatchStatus.CANDLING_DUE])
        ).all()

        updated = 0
        alerts = []

        for batch in active_batches:
            elapsed, alert = BatchService._compute_milestone(batch.set_date, batch.current_stage)
            if alert and batch.status != BatchStatus.CANDLING_DUE:
                batch.status = BatchStatus.CANDLING_DUE
                updated += 1
                alerts.append({
                    "batch_id": batch.batch_id,
                    "batch_code": batch.batch_code,
                    "elapsed_days": elapsed,
                    "alert": alert
                })
            elif not alert and batch.status == BatchStatus.CANDLING_DUE:
                batch.status = BatchStatus.INCUBATING
                updated += 1

        if updated > 0:
            db.commit()

        return MilestoneCheckResponse(
            evaluated_batches=len(active_batches),
            updated_batches=updated,
            alerts=alerts
        )

    @staticmethod
    def finalize_hatch(db: Session, batch_id: str, payload: FinalizeHatchPayload) -> BatchModel:
        batch = BatchService.get_batch(db, batch_id)
        
        if payload.hatched_count > batch.initial_egg_count:
            raise InvalidBatchStateTransitionException(
                f"Hatched count ({payload.hatched_count}) cannot exceed initial egg set count ({batch.initial_egg_count})."
            )

        batch.hatched_count = payload.hatched_count
        batch.unhatched_count = payload.unhatched_count if payload.unhatched_count is not None else (batch.initial_egg_count - payload.hatched_count)
        batch.current_stage = BatchStage.HATCHED
        batch.status = BatchStatus.COMPLETED
        if payload.notes:
            batch.notes = f"{batch.notes}\n[Final Hatch] {payload.notes}" if batch.notes else payload.notes

        db.commit()
        db.refresh(batch)
        return batch

    @staticmethod
    def delete_batch(db: Session, batch_id: str) -> bool:
        batch = BatchService.get_batch(db, batch_id)
        db.delete(batch)
        db.commit()
        return True

    @staticmethod
    def get_batch_summary(db: Session, batch_id: str) -> BatchSummaryResponse:
        batch = BatchService.get_batch(db, batch_id)

        totals = scan_totals(db, batch_id=batch_id)

        total_scanned = totals.scanned or 0
        fertile = totals.fertile or 0
        infertile = totals.infertile or 0
        manual_review = totals.manual_review or 0

        fertility_rate = (fertile / total_scanned * 100.0) if total_scanned > 0 else 0.0
        hatchability_rate = (batch.hatched_count / batch.initial_egg_count * 100.0) if batch.initial_egg_count > 0 else 0.0

        elapsed, alert = BatchService._compute_milestone(batch.set_date, batch.current_stage)

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
            hatched_count=batch.hatched_count,
            unhatched_count=batch.unhatched_count,
            total_scanned=total_scanned,
            fertile_count=fertile,
            infertile_count=infertile,
            manual_review_count=manual_review,
            fertility_rate=round(fertility_rate, 2),
            hatchability_rate=round(hatchability_rate, 2),
            notes=batch.notes,
            elapsed_days=elapsed,
            milestone_alert=alert
        )

    @staticmethod
    def get_batch_deep_analytics(db: Session, batch_id: str) -> BatchAnalyticsResponse:
        batch = BatchService.get_batch(db, batch_id)
        settings = db.query(HatcherySettingsModel).first()
        penoy_price = float(settings.penoy_unit_price_php) if settings else 14.00
        duckling_price = float(settings.duckling_unit_price_php) if settings else 40.00
        kwh_rate = float(settings.electricity_kwh_rate_php) if settings else 12.50
        kwh_per_egg = float(settings.kwh_saved_per_culled_egg) if settings else 0.2000

        # Day 10 primary stats
        d10_stats = scan_totals(db, batch_id=batch_id)

        d10_tot = d10_stats.scanned or 0
        d10_fer = d10_stats.fertile or 0
        d10_inf = d10_stats.infertile or 0
        d10_rev = d10_stats.manual_review or 0
        d10_rate = (d10_fer / d10_tot * 100.0) if d10_tot > 0 else 0.0

        # Financial values
        penoy_val = d10_inf * penoy_price
        power_saved = d10_inf * (kwh_rate * kwh_per_egg)
        duckling_rev = batch.hatched_count * duckling_price
        hatch_rate = (batch.hatched_count / batch.initial_egg_count * 100.0) if batch.initial_egg_count > 0 else 0.0

        # Candling runs
        sessions = db.query(CandlingSessionModel).filter(CandlingSessionModel.batch_id == batch_id).order_by(CandlingSessionModel.started_at.asc()).all()
        session_items = []
        for s in sessions:
            recorded = scan_totals(db, session_id=s.session_id)
            f_rate = (recorded.fertile / recorded.scanned * 100.0) if recorded.scanned else 0.0
            session_items.append(SessionSummaryItem(
                session_id=s.session_id,
                stage=s.stage.value,
                operator_name=s.operator_name,
                started_at=s.started_at,
                total_scanned=recorded.scanned,
                fertile_count=recorded.fertile,
                infertile_count=recorded.infertile,
                manual_review_count=recorded.manual_review,
                fertility_rate=round(f_rate, 2),
                avg_inference_ms=float(recorded.avg_inference_ms)
            ))

        elapsed, _ = BatchService._compute_milestone(batch.set_date, batch.current_stage)

        return BatchAnalyticsResponse(
            batch_id=batch.batch_id,
            batch_code=batch.batch_code,
            breed=batch.breed,
            incubator_id=batch.incubator_id,
            initial_egg_count=batch.initial_egg_count,
            set_date=batch.set_date,
            target_hatch_date=batch.target_hatch_date,
            current_stage=batch.current_stage,
            status=batch.status,
            elapsed_days=elapsed,
            total_scanned_day_10=d10_tot,
            fertile_day_10=d10_fer,
            infertile_penoy_day_10=d10_inf,
            manual_review_day_10=d10_rev,
            day_10_fertility_rate=round(d10_rate, 2),
            penoy_salvage_value_php=round(penoy_val, 2),
            electricity_saved_php=round(power_saved, 2),
            projected_duckling_revenue_php=round(duckling_rev, 2),
            hatched_count=batch.hatched_count,
            unhatched_count=batch.unhatched_count,
            actual_hatchability_rate=round(hatch_rate, 2),
            sessions=session_items
        )
