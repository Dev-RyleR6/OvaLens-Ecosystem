---
name: performance-auditor
description: Profiles and optimizes latency, throughput, memory, and frame rates across the Edge CV pipeline, FastAPI backend, and React dashboard.
---

# OvaLens Performance Auditor & Benchmark Protocol

This skill provides performance benchmarks, profiling techniques, and optimization guidelines for each subsystem in the OvaLens ecosystem.

---

## 🎯 1. Performance Target Benchmarks (SLOs)

| Subsystem | Metric | Target SLA / SLO | Critical Threshold |
| :--- | :--- | :--- | :--- |
| **Edge Vision (ONNX FP16)** | Inference Latency | $\le 35\text{ms}$ (RPi 5) / $\le 15\text{ms}$ (PC) | $> 50\text{ms}$ |
| **Camera Grabber** | Frame Pipeline Latency | Zero buffer lag ($< 10\text{ms}$) | $> 33\text{ms}$ |
| **Edge UI GUI** | Frame Rate | 60 FPS rendering | $< 30\text{FPS}$ |
| **ESP32 Actuation** | Sorting Stroke Timing | $\pm 5\text{ms}$ accuracy ($\Delta t = D/v$) | $> 20\text{ms}$ jitter |
| **Backend API** | Bulk Scan Ingestion (50 Scans) | $< 120\text{ms}$ | $> 350\text{ms}$ |
| **Dashboard** | Initial Page Load & Render | $< 1.2\text{s}$ (Lighthouse score $> 90$) | $> 2.5\text{s}$ |

---

## 🔬 2. Profiling Procedures by Subsystem

### A. Edge Computer Vision Benchmarking:
```python
import time
import numpy as np
from src.core.inference import InferenceEngine

engine = InferenceEngine()
dummy = np.zeros((720, 1280, 3), dtype=np.uint8)

# Benchmark 50 iterations
latencies = []
for _ in range(50):
    t0 = time.perf_counter()
    engine.predict(dummy)
    latencies.append((time.perf_counter() - t0) * 1000)

print(f"Mean Latency: {np.mean(latencies):.2f}ms | 95th Percentile: {np.percentile(latencies, 95):.2f}ms")
```

### B. Backend Database Connection Pool Profiling:
- Use connection pooling parameters in `app/core/database.py`:
  - `pool_size = 10`
  - `max_overflow = 20`
  - `pool_timeout = 30`
  - `pool_recycle = 1800`

### C. React Dashboard Rendering Optimization:
- Wrap heavy Recharts SVG graphs in `React.memo()`.
- Use TanStack Query stale time (`staleTime: 5000`) to eliminate redundant HTTP roundtrips.
- Keep bundle size minimal by lazy loading views (`React.lazy()`).

---

## 🛠️ 3. Optimization Playbook

1. **If Edge Inference is slow**:
   - Ensure model is running via ONNX Runtime with Graph Optimization level `ORT_ENABLE_ALL`.
   - Verify warmup dummy passes were executed on startup.
2. **If Camera Feed is lagging**:
   - Verify `cv2.CAP_PROP_BUFFERSIZE` is set to `1` to avoid OS video frame buffering.
3. **If Database Ingestion spikes CPU**:
   - Verify indexes exist on `egg_scans(session_id)`, `egg_scans(batch_id)`, `egg_scans(scanned_at)`.
   - Use `db.bulk_save_objects()` or PostgreSQL `INSERT INTO ... ON CONFLICT DO NOTHING`.
