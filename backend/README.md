# OvaLens Web API — Central Backend & Data Sync Engine

**OvaLens_web** is the central FastAPI backend server and database engine for the OvaLens Hatchery Ecosystem. It connects OvaLens Edge stations with the Hatchio Incubator Management System.

---

## 🌟 Key Features

- **FastAPI REST API**: High-performance async API for ingestion, analytics, session tracking, and dashboard integration.
- **PostgreSQL Database**: Relational database storage for incubation batches (`batches`), sessions (`sessions`), scan events (`scans`), and YOLO bounding box detections (`detections`).
- **Hatchio Firebase Sync Service (`services/firebase_writer.py`)**:
  - Automatically fetches active incubating batches from Hatchio's Firebase Realtime Database.
  - Automatically pushes aggregated candling results, egg counts, and fertility percentages to Hatchio upon scan ingestion.
- **Hatchio Dashboard Integration Endpoints**:
  - `GET /api/v1/hatchio/batches/candling-summary`: Provides aggregated batch metrics (fertility rate %, egg counts, stage metrics).
  - `GET /api/v1/hatchio/batches/{batch_id}/candling-details`: Serves per-egg tray and grid position classification breakdowns.
- **CORS Support**: Configured for web dashboard consumers (React, Next.js, Vite).

---

## 📁 Repository Structure

```
OvaLens_web/
├── server.py                   # FastAPI main application & SQLAlchemy models
├── services/
│   └── firebase_writer.py      # Hatchio Firebase RTDB reader & writer module
├── seed/                       # Database seed scripts for testing
├── scripts/                    # Maintenance & sync utility scripts
├── requirements.txt            # Python dependencies
└── .env                        # Database credentials, API keys, & Firebase host settings
```

---

## ⚙️ Setup & Execution

### Environment Variables (`.env`)
```env
DB_USER=postgres
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hatchery_db
API_KEY=your_secure_api_key
FIREBASE_HOST=hatchio-default-rtdb.firebaseio.com
```

### Running the Server
```bash
python server.py
```
The API server will run on `http://localhost:8000`. Swagger documentation is available at `http://localhost:8000/docs`.

### Web Dashboard
Open `http://localhost:8000/dashboard` to view the new lightweight OvaLens dashboard UI.
