import json
import urllib.request
import urllib.error
import uuid
from datetime import datetime, timezone

BASE = "http://127.0.0.1:8000"

def call(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:300]
    except Exception as e:
        return None, str(e)

print("1. Health:", call("GET", "/"))
print("2. Analytics:", call("GET", "/api/v1/analytics/summary"))
print("3. Sessions:", call("GET", "/api/v1/sessions"))
print("4. Scans list:", call("GET", "/api/v1/scans?limit=5"))
print("5. Scan 404:", call("GET", "/api/v1/scans/nonexistent-id"))

sid, scid = str(uuid.uuid4()), str(uuid.uuid4())
payload = {
    "scan_id": scid, "session_id": sid, "batch_code": "BATCH-CHECK",
    "stage": "DAY_10", "breed_code": "ITIM", "final_class": "INFERTILE",
    "confidence": 0.88, "inference_ms": 40,
    "scanned_at": datetime.now(timezone.utc).isoformat(),
    "detections": [{"class_label": "INFERTILE", "confidence": 0.88,
                    "bbox": [0.5, 0.5, 0.3, 0.4]}],
}
print("6. Sync new scan:", call("POST", "/api/v1/scans/sync", payload))
print("7. Sync duplicate:", call("POST", "/api/v1/scans/sync", payload))

bad = dict(payload, scan_id=str(uuid.uuid4()), breed_code="NOT_A_BREED")
print("8. Invalid enum:", call("POST", "/api/v1/scans/sync", bad))

bad2 = dict(payload, scan_id=str(uuid.uuid4()), scanned_at="not-a-date")
print("9. Bad date:", call("POST", "/api/v1/scans/sync", bad2))
