from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.settings import HatcherySettingsModel
from app.models.audit import AuditLogModel
from app.models.user import UserModel
from app.schemas.settings import HatcherySettingsResponse, HatcherySettingsUpdate
from app.api.deps import get_current_user, require_manager_or_admin

router = APIRouter()


def _get_or_create_settings(db: Session) -> HatcherySettingsModel:
    settings = db.query(HatcherySettingsModel).first()
    if not settings:
        settings = HatcherySettingsModel()
        db.add(settings)
        db.commit()
        db.refresh(settings)
    return settings


@router.get("", response_model=HatcherySettingsResponse, summary="Get facility configuration and economic parameters")
def get_settings(db: Session = Depends(get_db)):
    """Fetch current institutional settings, candling thresholds, and economic price rates."""
    return _get_or_create_settings(db)


@router.put("", response_model=HatcherySettingsResponse, summary="Update facility configuration")
def update_settings(
    payload: HatcherySettingsUpdate,
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    """Update facility branding, vision confidence thresholds, and economic prices."""
    settings = _get_or_create_settings(db)
    
    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    settings.updated_at = datetime.now(timezone.utc)
    
    # Audit log
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="SETTINGS_UPDATED",
        entity_type="HATCHERY_SETTINGS",
        entity_id=str(settings.setting_id),
        details={"updated_fields": list(update_data.keys()), "updated_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    db.refresh(settings)
    
    return settings


@router.post("/backups/create", summary="Trigger automated database snapshot")
def create_backup(
    db: Session = Depends(get_db),
    current_user: UserModel = Depends(require_manager_or_admin)
):
    from app.services.backup_service import BackupService
    result = BackupService.create_database_snapshot(db, triggered_by=current_user.email)
    
    audit = AuditLogModel(
        user_id=current_user.user_id,
        action="DATABASE_BACKUP_CREATED",
        entity_type="BACKUP",
        entity_id=result["filename"],
        details={"filename": result["filename"], "file_size_kb": result["file_size_kb"], "triggered_by": current_user.email}
    )
    db.add(audit)
    db.commit()
    return result


@router.get("/backups", summary="List database snapshot archives")
def list_backups(current_user: UserModel = Depends(require_manager_or_admin)):
    from app.services.backup_service import BackupService
    return BackupService.list_backups()
