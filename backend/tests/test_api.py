import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
    assert client.get("/api/v1/scans/search", params={"confidence": "REVIEW"}).json()["total"] == totals[0]
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


