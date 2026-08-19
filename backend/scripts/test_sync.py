try:
    import requests
except ImportError:
    print("❌ Error: 'requests' module not found. Install it with: pip install requests")
    exit(1)

import uuid
from datetime import datetime, timezone

URL = "http://localhost:8000/api/v1/scans/sync"

test_session_id = str(uuid.uuid4())
test_scan_id = str(uuid.uuid4())

payload = {
    "scan_id": test_scan_id,
    "session_id": test_session_id,
    "batch_code": "BATCH-TEST-2026",
    "stage": "DAY_10",
    "breed_code": "KAYUMANGGI",
    "final_class": "FERTILE",
    "confidence": 0.9425,
    "inference_ms": 38,
    "scanned_at": datetime.now(timezone.utc).isoformat(), # 👈 Updated timezone handling
    "routing_action": "ACCEPT",
    "image_url": f"local_scans/{test_scan_id}.jpg",
    "detections": [
        {
            "class_label": "FERTILE",
            "confidence": 0.9425,
            "bbox": [0.5123, 0.4891, 0.3201, 0.4102]
        }
    ]
}

print("🚀 Sending dummy scan payload to FastAPI server...")
try:
    response = requests.post(URL, json=payload, timeout=5)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"❌ Failed to reach server: {e}")