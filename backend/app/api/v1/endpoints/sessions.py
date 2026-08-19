from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.core.database import get_db
from app.models.session import CandlingSessionModel, CandlingStage
from app.models.batch import BatchModel, BatchStage
from app.schemas.session import SessionCreate, SessionEnd, SessionResponse
from app.api.deps import verify_api_key, get_current_user

router = APIRouter(prefix="/sessions", tags=["Candling Sessions"])


@router.get("", response_model=List[SessionResponse], summary="List candling sessions")
def list_sessions(
    batch_id: Optional[str] = None,
    stage: Optional[CandlingStage] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    query = db.query(CandlingSessionModel)
    if batch_id:
        query = query.filter(CandlingSessionModel.batch_id == batch_id)
    if stage:
        query = query.filter(CandlingSessionModel.stage == stage)
    return query.order_by(desc(CandlingSessionModel.started_at)).offset(offset).limit(limit).all()


@router.post("", response_model=SessionResponse, summary="Start a new candling session from Edge machine")
def create_session(
    payload: SessionCreate,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    # Verify batch exists
    batch = db.query(BatchModel).filter(BatchModel.batch_id == payload.batch_id).first()
    if not batch:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Batch '{payload.batch_id}' not found.")

    existing = db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == payload.session_id).first()
    if existing:
        return existing

    session = CandlingSessionModel(
        session_id=payload.session_id,
        batch_id=payload.batch_id,
        device_id=payload.device_id,
        stage=payload.stage,
        operator_name=payload.operator_name,
        started_at=payload.started_at
    )
    # Update batch current stage
    if payload.stage == CandlingStage.DAY_10:
        batch.current_stage = BatchStage.DAY_10
    elif payload.stage == CandlingStage.DAY_18:
        batch.current_stage = BatchStage.DAY_18
    elif payload.stage == CandlingStage.DAY_25:
        batch.current_stage = BatchStage.DAY_25

    db.add(session)
    db.commit()
    db.refresh(session)
    return session


@router.get("/{session_id}", response_model=SessionResponse, summary="Get session metrics by ID")
def get_session(session_id: UUID, db: Session = Depends(get_db)):
    session = db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")
    return session


@router.put("/{session_id}/end", response_model=SessionResponse, summary="Mark session as ended")
def end_session(
    session_id: UUID,
    payload: SessionEnd,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    session = db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Session '{session_id}' not found.")

    session.ended_at = payload.ended_at
    db.commit()
    db.refresh(session)
    return session
