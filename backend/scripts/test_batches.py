"""
Integration test for the Hatchio ↔ OvaLens batch & candling endpoints.

Prerequisites:
  - Server running on localhost:8000  (python server.py)
  - PostgreSQL reachable with .env configured
  - `requests` installed  (pip install requests)

Usage:
  python scripts/test_batches.py
"""

try:
    import requests
except ImportError:
    print("❌ Error: 'requests' module not found. Install it with: pip install requests")
    exit(1)

import os
import sys
from datetime import datetime, timezone

from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
API_KEY = os.getenv("API_KEY", "")  # Set if your server enforces API key

HEADERS = {"Content-Type": "application/json"}
if API_KEY:
    HEADERS["X-API-Key"] = API_KEY

BATCH_ID = "BATCH-TEST-2026-INT"
passed = 0
failed = 0


def report(label: str, ok: bool, detail: str = ""):
    global passed, failed
    icon = "✅" if ok else "❌"
    print(f"  {icon} {label}" + (f"  —  {detail}" if detail else ""))
    if ok:
        passed += 1
    else:
        failed += 1


# ---------------------------------------------------------------------------
# Step 0: Seed a batch directly via the DB (uses the /api/v1 helper or raw)
#   We create the batch by inserting through SQLAlchemy if possible, but since
#   we are a standalone script, we use psycopg2 for a quick seed.
# ---------------------------------------------------------------------------
print("\n🌱 Step 0: Seeding test batch into database...")

try:
    import psycopg2
    from dotenv import load_dotenv

    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "hatchery_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )
    conn.autocommit = True
    cur = conn.cursor()

    # Clean up any previous test data
    cur.execute("DELETE FROM candling_scans WHERE batch_id = %s", (BATCH_ID,))
    cur.execute("DELETE FROM batches WHERE batch_id = %s", (BATCH_ID,))

    cur.execute(
        """
        INSERT INTO batches (batch_id, breed, set_date, incubation_day, status, incubator_id, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            BATCH_ID,
            "Kayumanggi",
            datetime(2026, 7, 18, 6, 0, 0, tzinfo=timezone.utc),
            10,
            "CANDLING_DUE",
            "INC-UNIT-01",
            datetime.now(timezone.utc),
        ),
    )
    cur.close()
    conn.close()
    print("  ✅ Test batch seeded successfully.\n")
except Exception as e:
    print(f"  ⚠️  Could not seed batch via DB ({e}).")
    print("       Make sure PostgreSQL is running and .env is configured.\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Step 1: GET /api/v1/batches/active
# ---------------------------------------------------------------------------
print("📋 Step 1: GET /api/v1/batches/active")

resp = requests.get(f"{BASE_URL}/api/v1/batches/active", headers=HEADERS, timeout=5)
report("Status 200", resp.status_code == 200, f"got {resp.status_code}")
data = resp.json()
if not isinstance(data, list):
    report("Response is a list", False, f"got {type(data).__name__}: {data}")
    sys.exit(1)
report("Response is a list", True)

batch_ids = [b["batch_id"] for b in data]
report("Test batch present", BATCH_ID in batch_ids, f"found {len(data)} batches")

# Filter by status
resp2 = requests.get(
    f"{BASE_URL}/api/v1/batches/active",
    headers=HEADERS,
    params={"status": "CANDLING_DUE"},
    timeout=5,
)
report("Filter by status=CANDLING_DUE → 200", resp2.status_code == 200)
filtered = resp2.json()
report(
    "All returned batches have CANDLING_DUE status",
    all(b["status"] == "CANDLING_DUE" for b in filtered),
)

# Filter by incubator_id
resp3 = requests.get(
    f"{BASE_URL}/api/v1/batches/active",
    headers=HEADERS,
    params={"incubator_id": "INC-UNIT-01"},
    timeout=5,
)
report("Filter by incubator_id → 200", resp3.status_code == 200)

print()

# ---------------------------------------------------------------------------
# Step 2: POST /api/v1/candling/scans (valid)
# ---------------------------------------------------------------------------
print("📤 Step 2: POST /api/v1/candling/scans (valid payload)")

scan_payload = {
    "batch_id": BATCH_ID,
    "scanned_at": datetime.now(timezone.utc).isoformat(),
    "operator_id": "OP-TEST-001",
    "scans": [
        {"tray_id": "TRAY-A", "egg_position": "A1", "classification": "fertile", "confidence": 0.97},
        {"tray_id": "TRAY-A", "egg_position": "A2", "classification": "infertile", "confidence": 0.85},
        {"tray_id": "TRAY-A", "egg_position": "A3", "classification": "early_dead", "confidence": 0.72},
        {"tray_id": "TRAY-B", "egg_position": "B1", "classification": "fertile", "confidence": 0.94},
    ],
}

resp = requests.post(
    f"{BASE_URL}/api/v1/candling/scans", json=scan_payload, headers=HEADERS, timeout=5
)
report("Status 201 Created", resp.status_code == 201, f"got {resp.status_code}")

body = resp.json()
report("status == 'success'", body.get("status") == "success")
report("total_scans_recorded == 4", body.get("total_scans_recorded") == 4)
report(
    "classification_summary present",
    "classification_summary" in body,
    f"{body.get('classification_summary')}",
)

print()

# ---------------------------------------------------------------------------
# Step 3: POST /api/v1/candling/scans (invalid batch_id → 400)
# ---------------------------------------------------------------------------
print("🚫 Step 3: POST /api/v1/candling/scans (invalid batch_id)")

bad_payload = {
    "batch_id": "BATCH-DOES-NOT-EXIST",
    "scanned_at": datetime.now(timezone.utc).isoformat(),
    "scans": [
        {"tray_id": "TRAY-X", "egg_position": "X1", "classification": "fertile", "confidence": 0.50},
    ],
}

resp = requests.post(
    f"{BASE_URL}/api/v1/candling/scans", json=bad_payload, headers=HEADERS, timeout=5
)
report("Status 400 Bad Request", resp.status_code == 400, f"got {resp.status_code}")
report("Error detail mentions batch", "batch" in resp.json().get("detail", "").lower())

print()

# ---------------------------------------------------------------------------
# Cleanup & Summary
# ---------------------------------------------------------------------------
print("🧹 Cleaning up test data...")
try:
    conn = psycopg2.connect(
        dbname=os.getenv("DB_NAME", "hatchery_db"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASS"),
        host=os.getenv("DB_HOST", "localhost"),
        port=os.getenv("DB_PORT", "5432"),
    )
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("DELETE FROM candling_scans WHERE batch_id = %s", (BATCH_ID,))
    cur.execute("DELETE FROM batches WHERE batch_id = %s", (BATCH_ID,))
    cur.close()
    conn.close()
    print("  ✅ Cleaned up.\n")
except Exception:
    print("  ⚠️  Cleanup failed — test data may remain in DB.\n")

total = passed + failed
print(f"{'='*50}")
print(f"Results: {passed}/{total} passed" + (" 🎉" if failed == 0 else f" — {failed} FAILED ❌"))
print(f"{'='*50}")

sys.exit(0 if failed == 0 else 1)
