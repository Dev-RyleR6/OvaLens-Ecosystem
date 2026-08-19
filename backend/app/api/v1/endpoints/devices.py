from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.device import DeviceModel
from app.schemas.device import DeviceRegister, DeviceHeartbeat, DeviceResponse
from app.api.deps import verify_api_key, get_current_user

router = APIRouter(prefix="/devices", tags=["Edge Devices"])


@router.get("", response_model=List[DeviceResponse], summary="List all registered edge sorting stations")
def list_devices(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DeviceModel).all()


@router.post("/register", response_model=DeviceResponse, summary="Register or update an edge machine")
def register_device(
    payload: DeviceRegister,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == payload.device_id).first()
    if not device:
        device = DeviceModel(
            device_id=payload.device_id,
            device_name=payload.device_name,
            hardware_platform=payload.hardware_platform,
            model_version=payload.model_version,
            conveyor_speed_cm_s=payload.conveyor_speed_cm_s,
            conveyor_dist_cm=payload.conveyor_dist_cm,
            servo_pulse_ms=payload.servo_pulse_ms,
            last_heartbeat=datetime.now(timezone.utc)
        )
        db.add(device)
    else:
        device.device_name = payload.device_name
        device.hardware_platform = payload.hardware_platform
        device.model_version = payload.model_version
        device.conveyor_speed_cm_s = payload.conveyor_speed_cm_s
        device.conveyor_dist_cm = payload.conveyor_dist_cm
        device.servo_pulse_ms = payload.servo_pulse_ms
        device.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)
    return device


@router.post("/{device_id}/heartbeat", response_model=DeviceResponse, summary="Edge machine heartbeat ping")
def device_heartbeat(
    device_id: str,
    payload: DeviceHeartbeat,
    db: Session = Depends(get_db),
    api_key: str = Depends(verify_api_key)
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{device_id}' not registered.")

    device.status = payload.status
    if payload.ip_address:
        device.ip_address = payload.ip_address
    device.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)
    return device
