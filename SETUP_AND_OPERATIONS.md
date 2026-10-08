# OvaLens — Setup, Installation & Operator Manual

> **Foundation University Capstone Project**  
> Complete guide for setting up, configuring, installing dependencies, and operating the OvaLens duck egg candling and hatchery management ecosystem.

---

## 📋 System Prerequisites

Ensure the following runtimes and tools are installed on your workstation / edge hardware:

| Component | Minimum Version | Recommended | Notes |
| :--- | :--- | :--- | :--- |
| **Python** | 3.10+ | 3.11 or 3.12 | Used for both Backend API & Edge CV |
| **Node.js** | 18.x+ | 20.x or 22.x LTS | Used for React Dashboard |
| **npm** | 9.x+ | 10.x or 11.x | Node package manager |
| **PostgreSQL** | 15+ | 16.x | Main hatchery database engine |
| **Git** | 2.30+ | Latest | Monorepo version control |
| **Arduino IDE** | 2.x | Latest | For flashing ESP32 microcontroller |
| **Docker (Optional)** | 24+ | Latest | For 1-Click containerized deployment |

---

## 🛠️ Step-by-Step Installation & Setup

```
Capstone/
├── backend/       --> 1. Database & REST API Engine
├── edge/          --> 2. Computer Vision & Operator GUI
├── dashboard/     --> 3. React Web Management Dashboard
└── firmware/      --> 4. ESP32 Microcontroller Source Code
```

---

### Step 1: Central Backend & PostgreSQL Database Setup

1. **Navigate to the Backend Directory**:
   ```bash
   cd backend
   ```

2. **Install Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   Create a `.env` file in `backend/` (or copy from `.env.example`):
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

4. **Initialize & Seed PostgreSQL Database**:
   Run the database seeder to create all relational tables, register default users, and populate realistic duck egg batches:
   ```bash
   python -m seed.seed_db --reset
   ```

   **Default Seeded Credentials**:
   * **Admin**: `admin@ovalens.fu.edu.ph` / `Admin@123`
   * **Manager**: `manager@ovalens.fu.edu.ph` / `Manager@123`
   * **Operator**: `operator@ovalens.fu.edu.ph` / `Operator@123`

5. **Start the FastAPI Development Server**:
   ```bash
   python -m uvicorn app.main:app --reload --port 8000
   ```
   * **Interactive OpenAPI Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
   * **Health Endpoint**: [http://localhost:8000/api/v1/health](http://localhost:8000/api/v1/health)

---

### Step 2: Edge CV Application & Conveyor Controller Setup

1. **Navigate to the Edge Directory**:
   ```bash
   cd edge
   ```

2. **Install Edge Python Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Edge Environment**:
   Create a `.env` file in `edge/` (or copy from `.env.example`):
   ```ini
   API_KEY=dev-api-key-123
   API_BASE_URL=http://localhost:8000
   DEVICE_ID=STATION-01-RP5
   CAMERA_INDEX=0
   SERIAL_PORT=COM3
   SERIAL_BAUD=115200
   CONVEYOR_SPEED_CM_S=12.50
   CONVEYOR_DIST_CM=25.00
   SERVO_PULSE_MS=250
   ```

4. **Verify / Re-Export ONNX Model (Optional)**:
   The production ONNX model (`edge/models/weights/best.onnx`) is included. To re-export from raw `.pt` weights:
   ```bash
   python models/export_onnx.py
   ```

5. **Launch the Operator GUI Application**:
   ```bash
   python launcher.py
   ```

---

### Step 3: React Admin Web Dashboard Setup

1. **Navigate to the Dashboard Directory**:
   ```bash
   cd dashboard
   ```

2. **Install Node Modules**:
   ```bash
   npm install
   ```

3. **Start the Vite Development Server**:
   ```bash
   npm run dev
   ```
   Open **[http://localhost:5173](http://localhost:5173)** in your web browser.

4. **Build Production Bundle**:
   ```bash
   npm run build
   ```

---

### Step 4: ESP32 IoT Conveyor Firmware (Hardware Rig)

The current rig uses three ESP32 Dev Module boards at 115200 baud:

- **COM5**: `firmware/three_board/conveyor_esp32` (stepper).
- **COM7**: `firmware/three_board/egg_controller_esp32` (servo and IR).
- **COM9**: `firmware/three_board/light_controller_esp32` (candling light).

These sketches were installed on this rig. Rebuild/upload only when intentionally
updating firmware. See [wiring, calibration and verification](docs/EDGE_THREE_BOARD_IMPLEMENTATION.md).

---

## 🎮 How to Operate OvaLens in Production

### 1. Daily Startup Sequence

1. Connect camera 0 and the three ESP32s; power the rig.
2. Double-click **Start_OvaLens.cmd** in the repository root and enter the batch
   details. The camera preview starts automatically using remembered controls.
3. Check the empty conveyor, alignment and gate, then tick the inspection box.
4. Click **Start sorting** once. The app connects and prepares the saved station
   in the background. STOP remains available throughout preparation.
5. Start the backend/dashboard when network reporting is needed. Sorting records
   scans locally in SQLite and continues through network outages.

### 2. Conducting a Candling Run

1. Feed one Day 10 egg only when the large instruction says **Feed next egg**.
2. Wait through **Inspecting egg**, **Positioning gate** and **Wait ? egg passing**.
   Inference and boxes appear after the sensor stop is confirmed, lamp ON and
   camera settling; three agreeing fresh predictions are required.
3. Classification saves locally before the servo moves. The gate confirms its
   stroke before the stepper resumes, then holds its angle through gate exit.
4. Low confidence or disagreement holds the egg for manual review. Review choices
   appear when needed; STOP halts the station and finalizes local records.
5. At the target, final totals and **Start next batch** appear on the same screen.
   Configure the next batch, inspect the empty conveyor and Start sorting again.

Defaults: camera **0**, **COM5 stepper**, **COM7 servo + IR**, **COM9 light**. Saved
camera controls and gate calibration are retained. New three-board display hold
is **300ms**; pre-capture settling defaults to **1500ms** and evidence/servo checks are preserved.
Measured gate distances and physical acceptance remain required for the rig.

### 3. Keyboard Shortcuts & Tools

- **Space**: Single scan diagnostic, also under **Tools > Single scan**.
- **R**: STOP; it does not fire the diverter.
- **F1**: Operator guide.
- **F11**: Kiosk/windowed display.
- **Camera controls** above the preview (also **Tools > Camera controls**): Tune
  the idle camera while watching its image. Set Autofocus On, or choose Off and
  enter manual Focus. Exposure, gain, white balance and image controls are also
  available as sliders and exact numeric values. Drag, then Apply. **Range** edits
  a slider's tuning span; it does not claim driver-supported limits. Scroll to
  reach the remaining controls. Driver feedback reports
  unsupported requests; numeric ranges depend on the webcam.
- **Apply to preview** applies camera changes temporarily. **Save as default**
  applies and saves them for future launches. **Load saved settings** fills the
  form without applying. Blank values leave properties unchanged. Click **Done**
  and inspect the conveyor again before starting a session.
- **Camera controls > Cradle**: Confirm the path is clear, then **Connect for
  alignment**. The saved boards connect, the lamp turns on and the belt stays
  held. Choose a small step count and click Forward/Backward to position the
  cradle. Each move finishes with a hold; IR detection may stop it early. Switch
  to Camera to tune the stationary image. Done holds the belt and turns the lamp
  off. STOP [R] cancels motion. Re-inspect the empty rig before sorting.
- **Tools > Settings**: Advanced camera configuration, connections and measured calibration.
- **Tools > Retry camera preview**: Restart the preview after fixing its connection.

---

## 🐳 1-Click Docker Deployment (All-in-One)

To spin up PostgreSQL, the FastAPI Backend, and the React Web Dashboard together:

```bash
docker compose up --build
```
* **Web Dashboard**: [http://localhost:3000](http://localhost:3000)
* **Backend API & Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **PostgreSQL Database**: `localhost:5432`

---

## 🧪 Automated Testing Commands

To run all automated verification tests:

```bash
# Test 1: Backend REST API & Database Suite (6 tests)
cd backend
python -m pytest tests/test_api.py -v

# Test 2: Edge Computer Vision & Conveyor Suite (5 tests)
cd ../edge
python -m pytest tests/test_edge_pipeline.py -v
```

---

## Edge app availability and dashboard charts

The dashboard Overview includes recorded Day 10 classification and scans-versus-eggs-set charts. **Analytics & graphs** provides breed/status/batch filters, economic estimates, and batch forecasts. Charts, tables, and economic figures on Analytics share the selected scope. Overview Penoy estimates follow the selected batch. Missing records do not generate example results.

Classification totals are computed from persisted scan records, including their current manual overrides, rather than cached session counters. A scan event is not a unique egg: repeated scans can exceed the initial set count and can overstate Penoy quantity/value estimates. Awaiting-review counts are a subset of the two biological classifications. Forecasts use fixed breed assumptions and are estimates, not measured hatch outcomes or confirmed sales. Expand the exact-count tables below charts to inspect every value.

When launched through `edge/launcher.py` in normal operation, the edge app sends an authenticated device heartbeat every 15 seconds on a separate background thread. Configure `API_BASE_URL`, `API_KEY`, and a unique `DEVICE_ID` in `edge/.env`; the API key must match the backend configuration. Unknown stations register automatically; existing station calibration is preserved. Explicit simulation does not report a production station online.

The dashboard checks device records every 15 seconds, independently of the data refresh preference, and expires online status after 90 seconds without a heartbeat. Closing the app or losing connectivity therefore changes its status after the expiry period. “Backend API” indicates server connectivity; “Edge app connections” indicates recent app heartbeats. Neither confirms physical camera, serial controller, or conveyor readiness. Device heartbeat failures appear as sync attention in the edge app and leave locally saved scans intact.

## ❓ Troubleshooting FAQ

1. **Camera Feed is Black / Blank**:
   - Verify `CAMERA_INDEX` in `edge/.env`. On Windows with multiple webcams, try index `1` or `2`.
   - If the camera is unavailable, reconnect it and use **Tools > Retry camera preview**. Normal sorting never substitutes synthetic frames; preview simulation must be explicitly selected at startup.

2. **ESP32 Serial Connection Error**:
   - Check device manager for the COM port (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
   - Verify baud rate is set to `115200`.
   - If unplugged, the app automatically runs in **Mock Serial Mode** without crashing.

3. **Database Connection Refused**:
   - Ensure PostgreSQL service is running (`pg_isready`).
   - Check username/password in `backend/.env`.
