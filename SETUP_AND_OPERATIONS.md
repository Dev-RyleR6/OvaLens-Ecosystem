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
   uvicorn app.main:app --reload --port 8000
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

1. Open `firmware/esp32_actuator/esp32_actuator.ino` in **Arduino IDE**.
2. Install the **`ESP32Servo`** library via Arduino Library Manager.
3. Select Board: **ESP32 Dev Module**.
4. Connect the ESP32 via USB and upload the sketch.

---

## 🎮 How to Operate OvaLens in Production

### 1. Daily Startup Sequence
1. Start the **FastAPI Backend Server** (Port 8000).
2. Connect the **USB Camera** and **ESP32 Microcontroller** to the Edge Machine.
3. Power on the **10W Cree Candling Lamp** and **Conveyor Motor**.
4. Launch the **Edge Operator App** (`python launcher.py`).
5. Open the **React Admin Dashboard** (`http://localhost:5173` or port 3000 on Docker) on the hatchery manager's computer.

### 2. Conducting a Candling Run
1. In the Edge GUI, verify the **ESP32: CONNECTED** and **SYNC: ONLINE** status badges in the top right.
2. Click **▶ START CANDLING SESSION** (or press `[SPACEBAR]`).
3. Place duck eggs onto the motorized infeed lane.
4. As each egg passes over the candling aperture:
   * The **Optical Sensor** triggers a snapshot.
   * **YOLOv8 ONNX FP16** classifies the egg in $\le 30\text{ms}$.
   * If **`FERTILE`**: Egg passes freely to the incubator collection tray.
   * If **`INFERTILE`** or **`ABNORMAL`**: The ESP32 microsecond timer fires the servo flipper gate at the exact arrival moment ($\Delta t = D/v$), directing the egg into the cull chute.
5. Review real-time batch counts and the Day-10 Penoy salvage revenue on the Web Dashboard.

### 3. Keyboard Shortcuts & Overrides:
* **`[SPACEBAR]`**: Trigger manual candling scan.
* **`[R]`**: Manual diverter ejection override (fires servo kicker immediately).

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

## ❓ Troubleshooting FAQ

1. **Camera Feed is Black / Blank**:
   - Verify `CAMERA_INDEX` in `edge/.env`. On Windows with multiple webcams, try index `1` or `2`.
   - If no camera is plugged in, OvaLens automatically falls back to the **Synthetic Candling Stream Generator** for seamless offline testing.

2. **ESP32 Serial Connection Error**:
   - Check device manager for the COM port (e.g. `COM3` on Windows, `/dev/ttyUSB0` on Linux).
   - Verify baud rate is set to `115200`.
   - If unplugged, the app automatically runs in **Mock Serial Mode** without crashing.

3. **Database Connection Refused**:
   - Ensure PostgreSQL service is running (`pg_isready`).
   - Check username/password in `backend/.env`.
