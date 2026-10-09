import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


@pytest.fixture
def image_scan(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from uuid import uuid4
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.scan import EggScanModel
    from app.models.session import CandlingSessionModel

    session_id, scan_id = str(uuid4()), str(uuid4())
    headers = {"X-API-Key": settings.API_KEY}
    storage = tmp_path / "server_photos"
    storage.mkdir()
    monkeypatch.setattr(settings, "STORAGE_DIR", str(storage))
    # Exercise the actual public storage mount against isolated test evidence.
    mount = next(route.app for route in app.routes if getattr(route, "path", None) == "/storage")
    monkeypatch.setattr(mount, "directory", str(storage))
    monkeypatch.setattr(mount, "all_directories", [str(storage)])
    payload = {"scans": [{"scan_id": scan_id, "session_id": session_id,
        "batch_id": "BATCH-2026-08-KAY-01", "sequence_number": 910,
        "final_class": "FERTILE", "confidence": .95, "inference_ms": 20,
        "routing_action": "ACCEPT", "scanned_at": datetime.now(timezone.utc).isoformat()}]}
    try:
        assert client.post("/api/v1/scans/sync", headers=headers, json=payload).status_code == 200
        yield scan_id, headers, storage, payload
    finally:
        with SessionLocal() as db:
            db.query(EggScanModel).filter(EggScanModel.session_id == session_id).delete()
            db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).delete()
            db.commit()


def jpeg_bytes(color="red"):
    import io
    from PIL import Image
    stream = io.BytesIO()
    Image.new("RGB", (32, 24), color).save(stream, format="JPEG")
    return stream.getvalue()


def test_scan_photo_upload_replay_detail_and_public_image(image_scan):
    import hashlib
    scan_id, headers, storage, payload = image_scan
    data = jpeg_bytes()
    for _ in range(2):  # Lost acknowledgement replay must preserve identical bytes.
        response = client.post("/api/v1/scans/upload-image", headers=headers,
            data={"scan_id": scan_id}, files={"file": ("ignored-name.jpg", data, "image/jpeg")})
        assert response.status_code == 200, response.text
        ack = response.json()
        assert ack["scan_id"] == scan_id and ack["sha256"] == hashlib.sha256(data).hexdigest()
        assert ack["size_bytes"] == len(data)
        assert (storage / f"{scan_id}.jpg").read_bytes() == data
    assert client.get(ack["image_url"]).content == data
    assert client.post("/api/v1/scans/sync", headers=headers, json=payload).json()["duplicates_ignored"] == 1
    detail = client.get(f"/api/v1/scans/{scan_id}").json()
    assert detail["image_url"] == detail["thumbnail_url"] == ack["image_url"]
    items = client.get("/api/v1/scans/search", params={"q": scan_id}).json()["items"]
    assert len(items) == 1 and items[0]["image_url"] == ack["image_url"]


def test_scan_photo_invalid_unknown_and_unauthenticated_uploads(image_scan):
    from uuid import uuid4
    scan_id, headers, storage, _ = image_scan
    url = "/api/v1/scans/upload-image"
    assert client.post(url, data={"scan_id": scan_id}, files={"file": ("x.jpg", jpeg_bytes())}).status_code == 401
    assert client.post(url, headers=headers, data={"scan_id": str(uuid4())},
        files={"file": ("x.jpg", jpeg_bytes())}).status_code == 404
    for data in (b"not a photograph", jpeg_bytes()[:120]):
        assert client.post(url, headers=headers, data={"scan_id": scan_id},
            files={"file": ("x.jpg", data, "image/jpeg")}).status_code == 422
    assert not list(storage.iterdir())
    assert client.get(f"/api/v1/scans/{scan_id}").json()["image_url"] is None


def test_scan_photo_size_limit_and_conflicting_retry_preserve_evidence(image_scan, monkeypatch):
    from app.core.config import settings
    scan_id, headers, storage, _ = image_scan
    data = jpeg_bytes()
    def upload(data):
        return client.post("/api/v1/scans/upload-image", headers=headers, data={"scan_id": scan_id},
            files={"file": ("photo.jpg", data, "image/jpeg")})
    monkeypatch.setattr(settings, "MAX_SCAN_IMAGE_BYTES", len(data) - 1)
    assert upload(data).status_code == 413 and not list(storage.iterdir())
    monkeypatch.setattr(settings, "MAX_SCAN_IMAGE_BYTES", 10 * 1024 * 1024)
    assert upload(data).status_code == 200
    assert upload(jpeg_bytes("blue")).status_code == 409
    assert (storage / f"{scan_id}.jpg").read_bytes() == data


def test_scan_photo_storage_failure_is_atomic_and_retryable(image_scan, monkeypatch):
    from app.services import scan_images
    scan_id, headers, storage, _ = image_scan
    data = jpeg_bytes()
    replace = scan_images.os.replace
    monkeypatch.setattr(scan_images.os, "replace", lambda *a: (_ for _ in ()).throw(OSError("disk unavailable")))
    response = client.post("/api/v1/scans/upload-image", headers=headers, data={"scan_id": scan_id},
        files={"file": ("photo.jpg", data, "image/jpeg")})
    assert response.status_code == 503 and not list(storage.iterdir())
    assert client.get(f"/api/v1/scans/{scan_id}").json()["image_url"] is None
    monkeypatch.setattr(scan_images.os, "replace", replace)
    assert client.post("/api/v1/scans/upload-image", headers=headers, data={"scan_id": scan_id},
        files={"file": ("photo.jpg", data, "image/jpeg")}).status_code == 200


def test_saved_edge_photo_syncs_end_to_end_through_backend(image_scan, tmp_path, monkeypatch):
    """Actual SQLite outbox -> sync worker -> API -> PostgreSQL -> public JPEG."""
    from pathlib import Path
    import sys
    from app.core.config import settings
    sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "edge"))
    from src.db.local_db import LocalDatabaseManager
    from src.sync.sync_worker import BackgroundSyncWorker

    scan_id, headers, storage, payload = image_scan
    original = payload["scans"][0]
    local = LocalDatabaseManager(str(tmp_path / "edge" / "scans.db"))
    local.create_session(original["session_id"], original["batch_id"], "STATION-01-RP5", "DAY_10", "Test")
    # Use an existing Edge JPEG so the backend test needs no CV/camera packages.
    photo = tmp_path / "edge" / "local_scans" / f"{scan_id}.jpg"
    photo.parent.mkdir()
    photo.write_bytes(jpeg_bytes())
    local.record_scan(scan_id, original["session_id"], original["batch_id"], 910,
        "FERTILE", .95, 20, "ACCEPT", [], str(photo))
    worker = BackgroundSyncWorker(local, api_key=settings.API_KEY)
    worker._registered_sessions.add(original["session_id"])
    def post(url, **kwargs):
        kwargs.pop("timeout")
        return client.post(url.replace(worker.api_base_url, ""), **kwargs)
    monkeypatch.setattr("src.sync.sync_worker.requests.post", post)
    worker._perform_sync()
    assert local.get_unsynced_count() == 0 and worker.last_error is None
    detail = client.get(f"/api/v1/scans/{scan_id}").json()
    assert client.get(detail["image_url"]).content == Path(photo).read_bytes()
    assert (storage / f"{scan_id}.jpg").is_file()


def test_edge_heartbeat_authentication_and_persistence():
    from uuid import uuid4
    from datetime import datetime
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.device import DeviceModel

    device_id = f"TEST-{uuid4()}"
    headers = {"X-API-Key": settings.API_KEY}
    url = f"/api/v1/devices/{device_id}/heartbeat"
    assert client.post(url, json={"status": "ONLINE"}).status_code == 401
    assert client.post(url, json={"status": "ONLINE"}, headers=headers).status_code == 404
    try:
        registered = client.post('/api/v1/devices/register', headers=headers, json={
            'device_id': device_id, 'device_name': 'Heartbeat integration test', 'servo_pulse_ms': 321,
        })
        assert registered.status_code == 200
        for state in ('ONLINE', 'SCANNING'):
            result = client.post(url, headers=headers, json={'status': state})
            assert result.status_code == 200
            data = result.json()
            assert data['status'] == state
            assert data['servo_pulse_ms'] == 321
            assert datetime.fromisoformat(data['last_heartbeat']).tzinfo is not None
        with SessionLocal() as db:
            saved = db.get(DeviceModel, device_id)
            assert saved.status.value == 'SCANNING'
            assert saved.last_heartbeat is not None
    finally:
        with SessionLocal() as db:
            db.query(DeviceModel).filter(DeviceModel.device_id == device_id).delete()
            db.commit()


def test_scan_history_pagination_search_and_confidence_bands():
    first = client.get("/api/v1/scans/search", params={"limit": 2, "sort": "scanned_at", "order": "asc"})
    assert first.status_code == 200
    page = first.json()
    assert page["total"] > 100  # The seeded history must remain reachable beyond the old UI cap.
    assert len(page["items"]) == 2
    second = client.get("/api/v1/scans/search", params={"limit": 2, "offset": 2, "sort": "scanned_at", "order": "asc"}).json()
    assert second["total"] == page["total"]
    assert not ({item["scan_id"] for item in page["items"]} & {item["scan_id"] for item in second["items"]})
    older = client.get("/api/v1/scans/search", params={"limit": 2, "offset": 100}).json()
    assert older["items"]
    totals = []
    for band, lower, upper in [("LOW", 0, .75), ("MID", .75, .90), ("HIGH", .90, 1.01)]:
        response = client.get("/api/v1/scans/search", params={"confidence": band, "limit": 200})
        assert response.status_code == 200
        result = response.json()
        totals.append(result["total"])
        assert all(lower <= item["confidence"] < upper for item in result["items"])
    assert sum(totals) == page["total"]
    reviews = client.get("/api/v1/scans/search", params={"confidence": "REVIEW", "limit": 200}).json()
    assert all(item["routing_action"] == "MANUAL_REVIEW" or
               (item["confidence"] < .70 and not item["is_overridden"]) for item in reviews["items"])
    scan = page["items"][0]
    found = client.get("/api/v1/scans/search", params={"q": scan["scan_id"]}).json()
    assert found["total"] == 1
    assert found["items"][0]["scan_id"] == scan["scan_id"]
    batch = client.get("/api/v1/scans/search", params={"batch_id": scan["batch_id"], "final_class": scan["final_class"]}).json()
    assert all(item["batch_id"] == scan["batch_id"] and item["final_class"] == scan["final_class"] for item in batch["items"])
    assert client.get("/api/v1/scans/search", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/v1/scans/search", params={"sort": "unknown"}).status_code == 422
    assert client.get("/api/v1/scans/search", params={"offset": -1}).status_code == 422


def test_device_calibration_requires_authorization_and_persists():
    login = client.post("/api/v1/auth/login", json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    device = client.get("/api/v1/devices", headers=headers).json()[0]
    url = f"/api/v1/devices/{device['device_id']}"
    original = {key: device[key] for key in ("conveyor_speed_cm_s", "conveyor_dist_cm", "servo_pulse_ms")}
    assert client.patch(url, json=original).status_code == 401
    invalid = {**original, "conveyor_speed_cm_s": 0}
    assert client.patch(url, json=invalid, headers=headers).status_code == 422
    changed = {**original, "servo_pulse_ms": original["servo_pulse_ms"] + 1}
    try:
        response = client.patch(url, json=changed, headers=headers)
        assert response.status_code == 200
        stored = next(item for item in client.get("/api/v1/devices", headers=headers).json() if item["device_id"] == device["device_id"])
        assert stored["servo_pulse_ms"] == changed["servo_pulse_ms"]
    finally:
        assert client.patch(url, json=original, headers=headers).status_code == 200


def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


def test_login_and_me():
    # Login as seeded admin
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    assert login_resp.status_code == 200
    token_data = login_resp.json()
    assert "access_token" in token_data
    token = token_data["access_token"]

    # Access /me
    me_resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "admin@ovalens.fu.edu.ph"
    assert me_data["role"] == "ADMIN"


def test_list_batches():
    response = client.get("/api/v1/batches")
    assert response.status_code == 200
    batches = response.json()
    assert len(batches) >= 4


def test_analytics_overview():
    response = client.get("/api/v1/analytics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["total_eggs_scanned"] >= 500
    assert data["total_fertile"] + data["total_infertile"] == data["total_eggs_scanned"]
    assert data["total_fertile"] >= 0
    assert data["total_infertile"] >= 0
    assert data["overall_fertility_rate"] > 0.0


def test_graph_counts_ignore_drifted_session_counters():
    from sqlalchemy import func
    from app.core.database import SessionLocal
    from app.models.session import CandlingSessionModel
    from app.models.scan import EggScanModel, FertilityClass
    from app.models.settings import HatcherySettingsModel
    from app.services.batch_service import BatchService
    from app.services.analytics_service import AnalyticsService

    with SessionLocal() as db:
        session = db.query(CandlingSessionModel).filter(CandlingSessionModel.total_scanned > 0).first()
        batch_id = session.batch_id
        actual = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.batch_id == batch_id).scalar()
        infertile = db.query(func.count(EggScanModel.scan_id)).filter(EggScanModel.batch_id == batch_id, EggScanModel.final_class == FertilityClass.INFERTILE).scalar()
        # Deliberately corrupt only this uncommitted counter cache; rollback on exit.
        session.total_scanned += 999
        session.infertile_count += 999
        db.flush()
        summary = BatchService.get_batch_summary(db, batch_id)
        detailed = BatchService.get_batch_deep_analytics(db, batch_id)
        economics = AnalyticsService.get_economic_yield(db, batch_id=batch_id)
        assert summary.total_scanned == actual
        assert summary.fertile_count + summary.infertile_count == actual
        assert detailed.total_scanned_day_10 == actual
        assert sum(item.total_scanned for item in detailed.sessions) == actual
        assert detailed.infertile_penoy_day_10 == infertile
        assert economics.penoy_culled_day_10 == infertile
        price = float(db.query(HatcherySettingsModel).first().penoy_unit_price_php)
        assert economics.estimated_penoy_salvage_value_php == round(infertile * price, 2)
        assert AnalyticsService.get_economic_yield(db, batch_id='TEST-NONEXISTENT').total_economic_benefit_php == 0
        db.rollback()


def test_analytics_scopes_and_chart_totals_reconcile():
    batches = client.get('/api/v1/batches', params={'limit': 200}).json()
    overview = client.get('/api/v1/analytics/overview').json()
    assert sum(batch['total_scanned'] for batch in batches) == overview['total_eggs_scanned']
    assert sum(batch['fertile_count'] for batch in batches) == overview['total_fertile']
    assert sum(batch['infertile_count'] for batch in batches) == overview['total_infertile']
    for breed in ('KAYUMANGGI', 'ITIM', 'KHAKI'):
        for status in ('INCUBATING', 'CANDLING_DUE', 'COMPLETED'):
            selected = [batch for batch in batches if batch['breed'] == breed and batch['status'] == status]
            response = client.get('/api/v1/analytics/economic-yield', params={'breed': breed, 'status': status})
            assert response.status_code == 200
            economics = response.json()
            expected = sum(batch['infertile_count'] for batch in selected)
            assert economics['penoy_culled_day_10'] == expected
            assert economics['estimated_penoy_salvage_value_php'] == round(expected * economics['penoy_unit_price_php'], 2)
    assert client.get('/api/v1/analytics/economic-yield', params={'status': 'INVALID'}).status_code == 422


def test_forecast_with_scans_and_zero_fertile_never_uses_breed_baseline():
    from app.core.database import SessionLocal
    from app.models.scan import EggScanModel, FertilityClass
    from app.services.forecast_service import ForecastService

    with SessionLocal() as db:
        batch_id = db.query(EggScanModel.batch_id).first()[0]
        db.query(EggScanModel).filter(EggScanModel.batch_id == batch_id).update({'final_class': FertilityClass.INFERTILE})
        prediction = ForecastService.get_batch_forecast(db, batch_id)
        assert prediction.detected_fertility_rate == 0
        assert prediction.predicted_hatched_count == 0
        db.rollback()


def test_analytics_economic_yield():
    response = client.get("/api/v1/analytics/economic-yield")
    assert response.status_code == 200
    data = response.json()
    assert "penoy_culled_day_10" in data
    assert data["total_economic_benefit_php"] > 0


def test_pdf_and_csv_reports():
    # Test CSV
    csv_resp = client.get("/api/v1/reports/batch/BATCH-2026-08-KAY-01/csv")
    assert csv_resp.status_code == 200
    assert "Scan ID,Batch ID" in csv_resp.text

    # Test PDF
    pdf_resp = client.get("/api/v1/reports/batch/BATCH-2026-08-KAY-01/pdf")
    assert pdf_resp.status_code == 200
    assert pdf_resp.headers["content-type"] == "application/pdf"


def test_settings_endpoint():
    # Get settings
    resp = client.get("/api/v1/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["penoy_unit_price_php"] == 14.00
    assert data["duckling_unit_price_php"] == 40.00


def test_mortality_progression():
    resp = client.get("/api/v1/analytics/mortality-progression")
    assert resp.status_code == 200
    data = resp.json()
    assert data["day_10_outcome"]["day_marker"] == 10
    assert len(data["breed_breakdown"]) >= 3


def test_strict_day_10_two_class_contract():
    from pydantic import ValidationError
    from app.models.batch import BatchStage
    from app.models.scan import FertilityClass
    from app.models.session import CandlingStage
    from app.schemas.session import SessionCreate
    from datetime import datetime, timezone
    from uuid import uuid4

    assert {item.value for item in FertilityClass} == {"FERTILE", "INFERTILE"}
    assert {item.value for item in CandlingStage} == {"DAY_10"}
    assert "DAY_18" not in {item.value for item in BatchStage}
    assert "DAY_25" not in {item.value for item in BatchStage}

    with pytest.raises(ValidationError):
        SessionCreate(
            session_id=uuid4(), batch_id="BATCH-01", device_id="STATION-1",
            stage="DAY_18", operator_name="Tester", started_at=datetime.now(timezone.utc)
        )


def test_batch_analytics_and_milestones():
    # Check milestones
    ms_resp = client.post("/api/v1/batches/check-milestones")
    assert ms_resp.status_code == 200
    ms_data = ms_resp.json()
    assert "evaluated_batches" in ms_data

    # Batch Analytics
    an_resp = client.get("/api/v1/batches/BATCH-2026-08-KAY-01/analytics")
    assert an_resp.status_code == 200
    an_data = an_resp.json()
    assert an_data["batch_id"] == "BATCH-2026-08-KAY-01"
    assert "day_10_fertility_rate" in an_data
    assert "penoy_salvage_value_php" in an_data


def test_human_in_the_loop_override_audit_logging():
    # 1. Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]
    auth_headers = {"Authorization": f"Bearer {token}"}

    # 2. Fetch scans
    scans_resp = client.get("/api/v1/scans?limit=5")
    assert scans_resp.status_code == 200
    scans = scans_resp.json()
    assert len(scans) > 0
    target_scan = scans[0]
    scan_id = target_scan["scan_id"]

    # 3. Perform Human-in-the-loop override
    new_class = "INFERTILE" if target_scan["final_class"] == "FERTILE" else "FERTILE"
    override_resp = client.patch(
        f"/api/v1/scans/{scan_id}/override",
        json={"final_class": new_class, "reason": "Operator visual review confirmed embryo vein status"},
        headers=auth_headers
    )
    assert override_resp.status_code == 200
    updated_scan = override_resp.json()
    assert updated_scan["final_class"] == new_class
    assert updated_scan["routing_action"] == ("ACCEPT" if new_class == "FERTILE" else "REJECT")

    # 4. Verify audit log was recorded
    audit_resp = client.get("/api/v1/audit-logs?action=MANUAL_CLASSIFICATION_OVERRIDE", headers=auth_headers)
    assert audit_resp.status_code == 200
    audit_logs = audit_resp.json()
    assert len(audit_logs) > 0
    matching_log = next((l for l in audit_logs if l["entity_id"] == str(scan_id)), None)
    assert matching_log is not None
    assert matching_log["action"] == "MANUAL_CLASSIFICATION_OVERRIDE"
    assert matching_log["details"]["new_class"] == new_class
    assert "reason" in matching_log["details"]


def test_rbac_and_admin_security_protections():
    # 1. Login as admin
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    assert admin_login.status_code == 200
    admin_data = admin_login.json()
    admin_token = admin_data["access_token"]
    admin_id = admin_data["user"]["user_id"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Verify admin can list users
    users_resp = client.get("/api/v1/users", headers=admin_headers)
    assert users_resp.status_code == 200
    assert len(users_resp.json()) >= 1

    # 3. Verify self-deactivation guard on admin account
    self_toggle = client.patch(f"/api/v1/users/{admin_id}/status", headers=admin_headers)
    assert self_toggle.status_code == 400
    assert "Cannot suspend your own" in self_toggle.json()["detail"]

    # 4. Verify unauthenticated override is rejected
    unauth_override = client.patch(
        "/api/v1/scans/00000000-0000-0000-0000-000000000000/override",
        json={"final_class": "INFERTILE", "reason": "Testing unauth"}
    )
    assert unauth_override.status_code == 401


def test_hatch_yield_forecast_and_backup_service():
    # 1. Login as admin
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 2. Test Day 28 Biological Forecast Endpoint
    forecast_resp = client.get("/api/v1/batches/BATCH-2026-08-KAY-01/forecast")
    assert forecast_resp.status_code == 200
    forecast_data = forecast_resp.json()
    assert forecast_data["batch_id"] == "BATCH-2026-08-KAY-01"
    assert "predicted_hatched_count" in forecast_data
    assert "predicted_hatchability_rate" in forecast_data
    assert "projected_total_revenue_php" in forecast_data
    assert forecast_data["anomaly_status"] in ("OPTIMAL", "WARNING", "CRITICAL")
    assert len(forecast_data["advisory_notes"]) >= 1

    # 3. Test Database Backup Creation
    backup_create = client.post("/api/v1/settings/backups/create", headers=admin_headers)
    assert backup_create.status_code == 200
    backup_res = backup_create.json()
    assert backup_res["status"] == "success"
    assert backup_res["filename"].endswith(".json.gz")
    assert backup_res["file_size_kb"] > 0

    # 4. Test List Backups
    backups_list = client.get("/api/v1/settings/backups", headers=admin_headers)
    assert backups_list.status_code == 200
    assert len(backups_list.json()) >= 1
    backup_file = backups_list.json()[0]["filename"]

    # 5. Test Download Backup Endpoint
    download_resp = client.get(f"/api/v1/settings/backups/{backup_file}/download", headers=admin_headers)
    assert download_resp.status_code == 200
    assert download_resp.headers["content-type"] == "application/gzip"


def test_user_profile_and_password_change_flow():
    # 1. Login as admin and create dedicated test user
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    admin_token = admin_login.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    import time
    test_email = f"tester_{int(time.time())}@ovalens.fu.edu.ph"
    create_res = client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "email": test_email,
            "password": "InitialPassword@123",
            "full_name": "Test Operator Proponent",
            "role": "OPERATOR"
        }
    )
    assert create_res.status_code == 200

    # 2. Login as the newly created user
    user_login = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "InitialPassword@123"}
    )
    assert user_login.status_code == 200
    user_token = user_login.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 3. Update profile name
    update_prof = client.patch(
        "/api/v1/users/me/profile",
        json={"full_name": "Maria Clara (Updated Lead)"},
        headers=user_headers
    )
    assert update_prof.status_code == 200
    assert update_prof.json()["full_name"] == "Maria Clara (Updated Lead)"

    # 4. Fail password change on wrong current password
    bad_pw = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "WrongPassword999", "new_password": "NewSecretPassword@456"},
        headers=user_headers
    )
    assert bad_pw.status_code == 400
    assert "Current password verification failed" in bad_pw.json()["detail"]

    # 5. Success password change
    good_pw = client.patch(
        "/api/v1/users/me/password",
        json={"current_password": "InitialPassword@123", "new_password": "NewOperatorPass@789"},
        headers=user_headers
    )
    assert good_pw.status_code == 200
    assert good_pw.json()["status"] == "success"

    # 6. Verify login with new password
    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": test_email, "password": "NewOperatorPass@789"}
    )
    assert new_login.status_code == 200
    assert "access_token" in new_login.json()


def test_manual_review_routing_action_sync_and_metrics():
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.scan import EggScanModel, RoutingAction
    from app.models.session import CandlingSessionModel

    headers = {"X-API-Key": settings.API_KEY}
    test_session_id = str(uuid4())
    scan_id_1 = str(uuid4())
    scan_id_2 = str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    # Ingest 2 scans: one normal ACCEPT, one low-confidence MANUAL_REVIEW
    payload = {
        "scans": [
            {
                "scan_id": scan_id_1,
                "session_id": test_session_id,
                "batch_id": "BATCH-2026-08-KAY-01",
                "sequence_number": 901,
                "final_class": "FERTILE",
                "confidence": 0.9450,
                "inference_ms": 28,
                "routing_action": "ACCEPT",
                "cradle_index": 1,
                "aspect_ratio": 0.78,
                "vascular_index": 0.812,
                "detections": [],
                "scanned_at": now_iso
            },
            {
                "scan_id": scan_id_2,
                "session_id": test_session_id,
                "batch_id": "BATCH-2026-08-KAY-01",
                "sequence_number": 902,
                "final_class": "FERTILE",
                "confidence": 0.7100,
                "inference_ms": 32,
                "routing_action": "MANUAL_REVIEW",
                "cradle_index": 2,
                "aspect_ratio": 0.81,
                "vascular_index": 0.450,
                "detections": [],
                "scanned_at": now_iso
            }
        ]
    }

    try:
        sync_resp = client.post("/api/v1/scans/sync", json=payload, headers=headers)
        assert sync_resp.status_code == 200
        sync_data = sync_resp.json()
        assert sync_data["status"] == "success"
        assert sync_data["synced_count"] == 2

        # Verify session rolled up manual_review_count
        with SessionLocal() as db:
            session_record = db.get(CandlingSessionModel, test_session_id)
            assert session_record is not None
            assert session_record.total_scanned == 2
            assert session_record.manual_review_count == 1
            assert session_record.fertile_count == 2

        # Verify individual scan attributes
        scan_detail = client.get(f"/api/v1/scans/{scan_id_2}").json()
        assert scan_detail["routing_action"] == "MANUAL_REVIEW"
        assert scan_detail["cradle_index"] == 2
        assert scan_detail["aspect_ratio"] == 0.81
        assert scan_detail["vascular_index"] == 0.45
        assert scan_detail["is_overridden"] is False

    finally:
        with SessionLocal() as db:
            db.query(EggScanModel).filter(EggScanModel.session_id == test_session_id).delete()
            db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == test_session_id).delete()
            db.commit()


def test_seventy_percent_automatic_scans_sync_without_false_review_counts():
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.scan import EggScanModel
    from app.models.session import CandlingSessionModel
    from app.services.scan_metrics import scan_totals

    session_id = str(uuid4())
    cases = [("FERTILE", .70, "ACCEPT"), ("INFERTILE", .72, "REJECT"),
             ("FERTILE", .69, "MANUAL_REVIEW"), ("FERTILE", .95, "MANUAL_REVIEW")]
    scans = [{"scan_id": str(uuid4()), "session_id": session_id, "batch_id": "BATCH-2026-08-KAY-01",
              "sequence_number": 920 + index, "final_class": kind, "confidence": confidence,
              "inference_ms": 8, "routing_action": action, "scanned_at": datetime.now(timezone.utc).isoformat()}
             for index, (kind, confidence, action) in enumerate(cases)]
    try:
        for attempt in range(2):
            response = client.post("/api/v1/scans/sync", headers={"X-API-Key": settings.API_KEY}, json={"scans": scans})
            assert response.status_code == 200
            assert response.json()["synced_count"] == (4 if attempt == 0 else 0)
        with SessionLocal() as db:
            session = db.get(CandlingSessionModel, session_id)
            assert session.total_scanned == 4 and session.manual_review_count == 2
            totals = scan_totals(db, session_id=session_id)
            assert totals.scanned == 4 and totals.manual_review == 2
        for scan, (_, _, action) in zip(scans, cases):
            response = client.get("/api/v1/scans/search", params={"confidence": "REVIEW", "q": scan["scan_id"]})
            assert response.status_code == 200
            assert response.json()["total"] == int(action == "MANUAL_REVIEW")
    finally:
        with SessionLocal() as db:
            db.query(EggScanModel).filter(EggScanModel.session_id == session_id).delete()
            db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).delete()
            db.commit()


def test_edge_session_end_replay_preserves_time_counts_and_incubation_state(image_scan):
    from datetime import datetime, timedelta, timezone

    scan_id, headers, _, payload = image_scan
    session_id = payload["scans"][0]["session_id"]
    batch_id = payload["scans"][0]["batch_id"]
    before = client.get(f"/api/v1/batches/{batch_id}").json()
    ended_at = (datetime.fromisoformat(payload["scans"][0]["scanned_at"]) + timedelta(seconds=1)).astimezone(
        timezone(timedelta(hours=8))).isoformat()
    for _ in range(2):
        response = client.put(f"/api/v1/sessions/{session_id}/end", headers=headers, json={"ended_at": ended_at})
        assert response.status_code == 200
        body = response.json()
        assert datetime.fromisoformat(body["ended_at"]) == datetime.fromisoformat(ended_at)
        assert body["total_scanned"] == 1
    after = client.get(f"/api/v1/batches/{batch_id}").json()
    assert after["status"] == before["status"] and after["current_stage"] == before["current_stage"]


@pytest.mark.parametrize("stage,status,expected_stage", [
    ("SETTING", "INCUBATING", "DAY_10"),
    ("DAY_10", "CANDLING_DUE", "DAY_10"),
    ("HATCHED", "INCUBATING", "HATCHED"),
    ("COMPLETED", "COMPLETED", "COMPLETED"),
    ("COMPLETED", "ARCHIVED", "COMPLETED"),
])
def test_offline_session_registration_never_regresses_incubation(stage, status, expected_stage):
    from datetime import datetime, timedelta, timezone
    from uuid import uuid4
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.batch import BatchModel
    from app.models.session import CandlingSessionModel

    batch_id, session_id = f"SYNC-TEST-{uuid4()}", str(uuid4())
    now = datetime.now(timezone.utc)
    headers = {"X-API-Key": settings.API_KEY}
    try:
        with SessionLocal() as db:
            db.add(BatchModel(batch_id=batch_id, batch_code=batch_id, breed="KAYUMANGGI",
                incubator_id="TEST", initial_egg_count=1, set_date=now,
                target_hatch_date=now + timedelta(days=28), current_stage=stage, status=status))
            db.commit()
        for _ in range(2):
            response = client.post("/api/v1/sessions", headers=headers, json={
                "session_id": session_id, "batch_id": batch_id, "device_id": "STATION-01-RP5",
                "operator_name": "Test", "stage": "DAY_10", "started_at": now.isoformat()})
            assert response.status_code == 200
            assert response.json()["session_id"] == session_id
        batch = client.get(f"/api/v1/batches/{batch_id}").json()
        assert batch["current_stage"] == expected_stage and batch["status"] == status
    finally:
        with SessionLocal() as db:
            db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == session_id).delete()
            db.query(BatchModel).filter(BatchModel.batch_id == batch_id).delete()
            db.commit()


def test_scan_override_persists_is_overridden_and_reason():
    from uuid import uuid4
    from datetime import datetime, timezone
    from app.core.config import settings
    from app.core.database import SessionLocal
    from app.models.scan import EggScanModel
    from app.models.session import CandlingSessionModel

    # 1. Login to get token
    login_resp = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@ovalens.fu.edu.ph", "password": "Admin@123"}
    )
    auth_headers = {"Authorization": f"Bearer {login_resp.json()['access_token']}"}
    api_headers = {"X-API-Key": settings.API_KEY}

    test_session_id = str(uuid4())
    scan_id = str(uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        # Ingest test scan
        client.post("/api/v1/scans/sync", headers=api_headers, json={
            "scans": [{
                "scan_id": scan_id,
                "session_id": test_session_id,
                "batch_id": "BATCH-2026-08-KAY-01",
                "sequence_number": 999,
                "final_class": "INFERTILE",
                "confidence": 0.8200,
                "inference_ms": 25,
                "routing_action": "REJECT",
                "scanned_at": now_iso
            }]
        })

        # Override scan
        override_resp = client.patch(
            f"/api/v1/scans/{scan_id}/override",
            headers=auth_headers,
            json={"final_class": "FERTILE", "reason": "Operator confirmed viable spider veins"}
        )
        assert override_resp.status_code == 200
        data = override_resp.json()
        assert data["final_class"] == "FERTILE"
        assert data["routing_action"] == "ACCEPT"
        assert data["is_overridden"] is True
        assert data["override_reason"] == "Operator confirmed viable spider veins"
        assert data["overridden_at"] is not None

        # Verify get_scan returns is_overridden
        detail_resp = client.get(f"/api/v1/scans/{scan_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert detail["is_overridden"] is True
        assert detail["override_reason"] == "Operator confirmed viable spider veins"

    finally:
        with SessionLocal() as db:
            db.query(EggScanModel).filter(EggScanModel.scan_id == scan_id).delete()
            db.query(CandlingSessionModel).filter(CandlingSessionModel.session_id == test_session_id).delete()
            db.commit()
