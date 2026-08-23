import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
    assert len(data["overall_stages"]) == 3
    assert len(data["breed_breakdown"]) >= 3


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




