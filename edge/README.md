# OvaLens — Edge Device App for Automated Duck Egg Candling

**OvaLens** is an offline-first desktop/edge application designed for hatchery operators to perform computer-vision-assisted duck egg candling, fertility classification, and batch tracking.

---

## 🌟 Key Features

- **Computer Vision Model Execution**: Runs YOLO-based object detection models for real-time fertility classification (`fertile`, `infertile`, `early_dead`/`abnormal`).
- **Hatchio Batch Sync**: Automatically fetches active incubation batches from `OvaLens_web` API (which syncs from Hatchio's Firebase Database).
- **Offline Scan Storage**: Stores scan sessions and per-egg classifications locally when network connectivity is unavailable.
- **Auto Sync Worker**: Background thread automatically uploads stored scan records and bounding box detections to the `OvaLens_web` central server once online.
- **Operator GUI**: Clean desktop interface built with Python/Tkinter for tray selection, egg positioning, live camera view, and manual override options.

---

## 📁 Repository Structure

```
OvaLens/
├── launcher.py         # Main GUI Application entry point & background sync worker
├── db/                 # Local SQLite database for offline scan persistence
├── models/             # PyTorch / YOLO vision model weights (.pt files)
├── local_scans/        # Local cache for captured scan images
└── .env                # Edge device configuration (API URLs & keys)
```

---

## ⚙️ Setup & Execution

### Prerequisites
- Python 3.9+
- OpenCV, PyTorch, Ultralytics YOLO, Pillow, Requests, SQLite3

### Launching the Application
```bash
python launcher.py
```

---

## 🔗 Integration Flow

1. On launch, OvaLens Edge App calls `GET /api/v1/batches/active` on `OvaLens_web` to retrieve active incubation batches created in Hatchio.
2. Operator candles eggs and confirms results in the GUI.
3. The app posts classification results to `POST /api/v1/candling/scans` on `OvaLens_web` for central reporting and automatic Hatchio dashboard sync.
