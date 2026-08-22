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

