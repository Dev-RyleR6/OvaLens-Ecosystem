import os
import gzip
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.user import UserModel
from app.models.device import DeviceModel
from app.models.batch import BatchModel
from app.models.session import CandlingSessionModel
from app.models.scan import EggScanModel
from app.models.settings import HatcherySettingsModel
from app.models.audit import AuditLogModel

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "backups")


class BackupService:
    """
    Automated Hatchery Database Backup & Snapshot Engine.
    Creates compressed, serialized snapshots of all PostgreSQL tables.
    """

    @staticmethod
    def create_database_snapshot(db: Session, triggered_by: str = "System Automated") -> Dict[str, Any]:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        filename = f"ovalens_backup_{timestamp}.json.gz"
        filepath = os.path.join(BACKUP_DIR, filename)

        # 1. Extract database records
        users = [
            {"user_id": str(u.user_id), "email": u.email, "full_name": u.full_name, "role": u.role.value, "is_active": u.is_active}
            for u in db.query(UserModel).all()
        ]
        devices = [
            {"device_id": d.device_id, "device_name": d.device_name, "hardware_platform": d.hardware_platform, "model_version": d.model_version}
            for d in db.query(DeviceModel).all()
        ]
        batches = [
            {
                "batch_id": b.batch_id,
                "batch_code": b.batch_code,
                "breed": b.breed.value,
                "incubator_id": b.incubator_id,
                "initial_egg_count": b.initial_egg_count,
                "current_stage": b.current_stage.value,
                "status": b.status.value,
                "hatched_count": b.hatched_count,
                "unhatched_count": b.unhatched_count,
                "set_date": b.set_date.isoformat(),
            }
            for b in db.query(BatchModel).all()
        ]
        sessions = [
            {
                "session_id": str(s.session_id),
                "batch_id": s.batch_id,
                "stage": s.stage.value,
                "operator_name": s.operator_name,
                "total_scanned": s.total_scanned,
                "fertile_count": s.fertile_count,
                "infertile_count": s.infertile_count,
                "abnormal_count": s.abnormal_count,
                "started_at": s.started_at.isoformat(),
            }
            for s in db.query(CandlingSessionModel).all()
        ]
        scans = [
            {
                "scan_id": str(sc.scan_id),
                "session_id": str(sc.session_id),
                "batch_id": sc.batch_id,
                "sequence_number": sc.sequence_number,
                "final_class": sc.final_class.value,
                "confidence": sc.confidence,
                "routing_action": sc.routing_action.value,
                "scanned_at": sc.scanned_at.isoformat(),
            }
            for sc in db.query(EggScanModel).all()
        ]
        settings_record = db.query(HatcherySettingsModel).first()
        settings_data = {
            "facility_name": settings_record.facility_name if settings_record else "Foundation University Hatchery",
            "penoy_unit_price_php": float(settings_record.penoy_unit_price_php) if settings_record else 14.0,
            "duckling_unit_price_php": float(settings_record.duckling_unit_price_php) if settings_record else 40.0,
        }

        backup_payload = {
            "version": "2.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "triggered_by": triggered_by,
            "records_count": {
                "users": len(users),
                "devices": len(devices),
                "batches": len(batches),
                "sessions": len(sessions),
                "scans": len(scans),
            },
            "data": {
                "settings": settings_data,
                "users": users,
                "devices": devices,
                "batches": batches,
                "sessions": sessions,
                "scans": scans,
            }
        }

        # 2. Write compressed gzip archive
        json_bytes = json.dumps(backup_payload, indent=2, default=str).encode("utf-8")
        with gzip.open(filepath, "wb") as gz_file:
            gz_file.write(json_bytes)

        file_size_bytes = os.path.getsize(filepath)

        return {
            "status": "success",
            "filename": filename,
            "filepath": filepath,
            "file_size_kb": round(file_size_bytes / 1024, 2),
            "created_at": backup_payload["created_at"],
            "records_summary": backup_payload["records_count"],
        }

    @staticmethod
    def list_backups() -> List[Dict[str, Any]]:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        files = [f for f in os.listdir(BACKUP_DIR) if f.endswith(".json.gz")]
        files.sort(reverse=True)

        results = []
        for filename in files:
            filepath = os.path.join(BACKUP_DIR, filename)
            size_kb = round(os.path.getsize(filepath) / 1024, 2)
            results.append({
                "filename": filename,
                "file_size_kb": size_kb,
                "created_at": datetime.fromtimestamp(os.path.getctime(filepath), timezone.utc).isoformat()
            })
        return results
