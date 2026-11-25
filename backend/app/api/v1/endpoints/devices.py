from datetime import datetime, timezone
from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
import requests

from app.core.database import get_db
from app.models.device import DeviceModel, DeviceStatus
from app.schemas.device import DeviceRegister, DeviceHeartbeat, DeviceResponse, DeviceCalibrationUpdate
from app.api.deps import verify_api_key, get_current_user, require_manager_or_admin

router = APIRouter(prefix="/devices", tags=["Edge Devices"])


@router.get("", response_model=List[DeviceResponse], summary="List all registered edge sorting stations")
def list_devices(db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    return db.query(DeviceModel).all()


@router.get("/{device_id}", response_model=DeviceResponse, summary="Get details for a single edge sorting station")
def get_device(
    device_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{device_id}' not found.")
    return device


@router.get("/{device_id}/live", summary="Fetch real-time diagnostics directly from the edge app")
def get_device_live(
    device_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Device '{device_id}' not found.")

    edge_url = device.edge_url or (f"http://{device.ip_address}:8008" if device.ip_address else "http://localhost:8008")
    
    # Actively probe the Edge App's real HTTP server
    try:
        resp = requests.get(f"{edge_url}/api/device", timeout=2.0)
        if resp.status_code == 200:
            payload = resp.json()
            live_data = payload.get("device", payload)
            
            # Update database record with fresh live state
            device.telemetry = live_data
            if live_data.get("status"):
                try:
                    device.status = DeviceStatus(live_data["status"])
                except Exception:
                    device.status = DeviceStatus.ONLINE
            else:
                device.status = DeviceStatus.ONLINE

            if live_data.get("ip_address"):
                device.ip_address = live_data["ip_address"]
            if live_data.get("hardware_platform"):
                device.hardware_platform = live_data["hardware_platform"]
            if live_data.get("ai_model", {}).get("model_version"):
                device.model_version = live_data["ai_model"]["model_version"]
            device.edge_url = edge_url
            device.last_heartbeat = datetime.now(timezone.utc)
            db.commit()
            db.refresh(device)

            return {
                "device_id": device_id,
                "is_live": True,
                "edge_url": edge_url,
                "device": device,
                "telemetry": live_data
            }
    except Exception:
        pass

    return {
        "device_id": device_id,
        "is_live": False,
        "edge_url": edge_url,
        "device": device,
        "telemetry": device.telemetry or {}
    }


@router.get("/{device_id}/preview", summary="Proxy real-time camera snapshot from edge app")
def get_device_camera_preview(
    device_id: str,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")

    edge_url = device.edge_url or (f"http://{device.ip_address}:8008" if device.ip_address else "http://localhost:8008")
    try:
        resp = requests.get(f"{edge_url}/camera/snapshot", timeout=2.5)
        if resp.status_code == 200:
            return Response(content=resp.content, media_type="image/jpeg")
    except Exception:
        pass
    raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Edge camera frame unavailable.")


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
            ip_address=payload.ip_address,
            edge_url=payload.edge_url,
            telemetry=payload.telemetry,
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
        if payload.ip_address:
            device.ip_address = payload.ip_address
        if payload.edge_url:
            device.edge_url = payload.edge_url
        if payload.telemetry:
            device.telemetry = payload.telemetry
        device.conveyor_speed_cm_s = payload.conveyor_speed_cm_s
        device.conveyor_dist_cm = payload.conveyor_dist_cm
        device.servo_pulse_ms = payload.servo_pulse_ms
        device.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)
    return device


@router.patch("/{device_id}", response_model=DeviceResponse, summary="Save device calibration record")
def update_device_calibration(
    device_id: str,
    payload: DeviceCalibrationUpdate,
    db: Session = Depends(get_db),
    current_user = Depends(require_manager_or_admin),
):
    device = db.query(DeviceModel).filter(DeviceModel.device_id == device_id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Device not found.")
    for key, value in payload.model_dump().items():
        setattr(device, key, value)
    db.commit()
    db.refresh(device)
    # This updates the database only; no hardware acknowledgement is implied.
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
    if payload.edge_url:
        device.edge_url = payload.edge_url
    if payload.hardware_platform:
        device.hardware_platform = payload.hardware_platform
    if payload.model_version:
        device.model_version = payload.model_version
    if payload.telemetry:
        device.telemetry = payload.telemetry
    device.last_heartbeat = datetime.now(timezone.utc)

    db.commit()
    db.refresh(device)
    return device
