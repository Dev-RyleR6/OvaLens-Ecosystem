"""Aggregate persisted scans rather than mutable session counter caches."""
from sqlalchemy import case, func, or_, and_
from sqlalchemy.orm import Session
from app.models.scan import EggScanModel, FertilityClass, RoutingAction
from app.models.batch import BatchModel


def review_condition():
    """Keep explicit reviews and flag unreviewed results below the sorting floor."""
    return or_(EggScanModel.routing_action == RoutingAction.MANUAL_REVIEW,
               and_(EggScanModel.confidence < .70, EggScanModel.is_overridden.is_(False)))


def scan_totals(db: Session, batch_id=None, breed=None, status=None, session_id=None):
    review = review_condition()
    query = db.query(
        func.count(EggScanModel.scan_id).label("scanned"),
        func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.FERTILE, 1), else_=0)), 0).label("fertile"),
        func.coalesce(func.sum(case((EggScanModel.final_class == FertilityClass.INFERTILE, 1), else_=0)), 0).label("infertile"),
        func.coalesce(func.sum(case((review, 1), else_=0)), 0).label("manual_review"),
        func.coalesce(func.avg(EggScanModel.inference_ms), 0).label("avg_inference_ms"),
    ).join(BatchModel, EggScanModel.batch_id == BatchModel.batch_id)
    if batch_id:
        query = query.filter(BatchModel.batch_id == batch_id)
    if breed:
        query = query.filter(BatchModel.breed == breed)
    if status:
        query = query.filter(BatchModel.status == status)
    if session_id:
        query = query.filter(EggScanModel.session_id == session_id)
    return query.one()
