# OvaLens Central Backend — FastAPI & PostgreSQL 16 Data Engine

> **Subsystem**: `backend/`  
> **Platform**: Python 3.11+ / FastAPI / SQLAlchemy 2.0 / PostgreSQL 16  
> **License**: Apache License 2.0  

**OvaLens Backend** is the high-performance central REST API server, database engine, and analytics service for the entire duck hatchery ecosystem. It manages incubation batches, ingest candling scans idempotently from edge stations, computes hatchery economics, and generates official audit reports.

---

## 🌟 Key Features

* **Modular FastAPI Architecture**: Clean layered structure (`core/`, `models/`, `schemas/`, `api/v1/`, `services/`).
* **PostgreSQL 16 Relational Schema**: Declarative SQLAlchemy 2.0 models for `users`, `devices`, `batches`, `candling_sessions`, `egg_scans` (with JSONB bounding boxes), and `audit_logs`.
* **Idempotent Ingestion**: `POST /api/v1/scans/sync` uses PostgreSQL `ON CONFLICT (scan_id) DO NOTHING` to prevent duplicate network sync records.
* **Hatchery Economics**: Computes Day-10 Penoy salvage revenue, energy savings from freed incubator capacity, and mortality distributions.
* **Automated Audit Exporters**: Direct streaming of dynamic CSV datasets and official ReportLab PDF candling inspection certificates.
* **Role-Based Access Control (RBAC)**: JWT authentication with bcrypt password hashing and API Key authentication for machine stations.

---

## 📁 Subsystem Directory Structure

```
backend/
├── app/
│   ├── core/                     # Config (Settings), DB session, JWT security, exceptions
│   ├── models/                   # SQLAlchemy 2.0 declarative models
│   ├── schemas/                  # Pydantic v2 DTOs (Request / Response validation)
│   ├── api/                      # Modular API routers & dependency injection
│   │   ├── deps.py               # Security & DB dependencies
│   │   └── v1/endpoints/         # auth, devices, batches, sessions, scans, analytics, reports
│   ├── services/                 # Batch lifecycle, analytics math, PDF/CSV generation
│   └── main.py                   # FastAPI application entry point, CORS, exception handlers
├── seed/
│   └── seed_db.py                # Rich database seeder CLI for testing & defense
├── tests/
│   └── test_api.py               # Automated pytest REST API test suite
├── Dockerfile                    # Containerization specification
└── requirements.txt              # Backend Python dependencies
```

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`backend/.env`)
```ini
DB_USER=postgres
DB_PASS=your_password
DB_HOST=localhost
DB_PORT=5432
DB_NAME=hatchery_db
API_KEY=dev-api-key-123
JWT_SECRET=super-secret-jwt-key-ovalens-capstone-2026
ENVIRONMENT=development
```

### 3. Initialize & Seed Database
```bash
python -m seed.seed_db --reset
```

### 4. Start Development Server
```bash
python -m uvicorn app.main:app --reload --port 8000
```
* **Interactive OpenAPI (Swagger) Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **API Health Check**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

### 5. Run Automated Tests
```bash
python -m pytest tests/test_api.py -v
```
