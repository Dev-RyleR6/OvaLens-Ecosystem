from typing import List
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert

from app.models.scan import EggScanModel, FertilityClass, RoutingAction
from app.models.session import CandlingSessionModel, CandlingStage
from app.schemas.scan import ScanSyncPayload, ScanSyncResponse
from app.core.exceptions import EntityNotFoundException


class ScanService:
    @staticmethod
    def sync_scans(db: Session, payload: ScanSyncPayload) -> ScanSyncResponse:
        if not payload.scans:
            return ScanSyncResponse(total_received=0, synced_count=0, duplicates_ignored=0)

        first_scan = payload.scans[0]
        session_id = first_scan.session_id

        # Verify session exists; if not (e.g. edge was offline during session start), auto-provision it
        session = db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).first()
        if not session:
            session = CandlingSessionModel(
                session_id=session_id,
                batch_id=first_scan.batch_id,
                device_id="STATION-01-RP5",
                stage=CandlingStage.DAY_10,
                operator_name="Edge Conveyor Operator",
                started_at=first_scan.scanned_at
            )
            db.add(session)
            db.flush()

        # Prepare scan records
        values_to_insert = [
            {
                "scan_id": item.scan_id,
                "session_id": item.session_id,
                "batch_id": item.batch_id,
                "sequence_number": item.sequence_number,
                "final_class": item.final_class,
                "confidence": item.confidence,
                "inference_ms": item.inference_ms,
                "routing_action": item.routing_action,
                "image_url": item.image_url,
                "detections": item.detections,
                "scanned_at": item.scanned_at
            }
            for item in payload.scans
        ]

        # PostgreSQL Atomic Idempotent Insert (ON CONFLICT DO NOTHING)
        stmt = insert(EggScanModel).values(values_to_insert)
        stmt = stmt.on_conflict_do_nothing(index_elements=["scan_id"])
        result = db.execute(stmt)
        synced_count = result.rowcount
        duplicates_ignored = len(payload.scans) - synced_count

        # Recalculate and update session rollup totals atomically
        aggregates = db.query(
            func.count(EggScanModel.scan_id).label("total"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.ABNORMAL, 1), else_=0)), 0).label("abnormal"),
            func.coalesce(func.avg(EggScanModel.inference_ms), 0.0).label("avg_lat")
        ).filter(EggScanModel.session_id == session_id).first()

        session.total_scanned = aggregates.total or 0
        session.fertile_count = aggregates.fertile or 0
        session.infertile_count = aggregates.infertile or 0
        session.abnormal_count = aggregates.abnormal or 0
        session.avg_inference_ms = round(float(aggregates.avg_lat or 0.0), 2)

        db.commit()

        return ScanSyncResponse(
            status="success",
            total_received=len(payload.scans),
            synced_count=synced_count,
            duplicates_ignored=duplicates_ignored,
            session_id=session_id
        )

    @staticmethod
    def override_scan(db: Session, scan_id: UUID, final_class: FertilityClass) -> EggScanModel:
        scan = db.query(EggScanModel).filter(EggScanModel.scan_id == scan_id).first()
        if not scan:
            raise EntityNotFoundException(f"Scan '{scan_id}' not found.")

        scan.final_class = final_class
        scan.routing_action = RoutingAction.ACCEPT if final_class == FertilityClass.FERTILE else RoutingAction.REJECT
        db.flush()

        # Recalculate parent session rollup counters
        aggregates = db.query(
            func.count(EggScanModel.scan_id).label("total"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile"),
            func.coalesce(func.sum(func.case((EggScanModel.final_class == FertilityClass.ABNORMAL, 1), else_=0)), 0).label("abnormal"),
            func.coalesce(func.avg(EggScanModel.inference_ms), 0.0).label("avg_lat")
        ).filter(EggScanModel.session_id == scan.session_id).first()

        session = db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == scan.session_id).first()
        if session and aggregates:
            session.total_scanned = aggregates.total or 0
            session.fertile_count = aggregates.fertile or 0
            session.infertile_count = aggregates.infertile or 0
            session.abnormal_count = aggregates.abnormal or 0
            session.avg_inference_ms = round(float(aggregates.avg_lat or 0.0), 2)

        db.commit()
        db.refresh(scan)
        return scan
