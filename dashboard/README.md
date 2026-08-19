# OvaLens Dashboard — React 18 Admin & Hatchery Management Portal

> **Subsystem**: `dashboard/`  
> **Platform**: Web (React 18 + Vite 5 + TypeScript + TailwindCSS)  
> **License**: Apache License 2.0  

**OvaLens Dashboard** is the central web application for hatchery managers, quality control auditors, and researchers at Foundation University. It provides real-time visualization of egg candling operations, batch developmental lifecycles, Day-10 Penoy economic salvage estimators, and IoT station telemetry.

---

## 🌟 Key Features

* **Foundation University Brand Aesthetic**: Built with custom theme tokens (`#800000` Maroon, `#357a38` Agri-Green, `#DC2626` Reject Red, `#0F172A` Slate Dark Theme).
* **Executive Overview**: Real-time KPI StatCards, breed distribution bar charts, fertility rate donut charts, and live conveyor scan feed stream.
* **Incubation Batch Management**: Full 28-day lifecycle progress tracking, "Set New Batch" modal, and direct CSV/PDF audit report download triggers.
* **Candling Scan Explorer**: Dual Grid/Table viewer with synthetic candling frames, bounding box HUD, and JSONB inspection drawer.
* **Hatchery Economics & Analytics**: Interactive Day-10 Penoy Economic Salvage Yield Estimator (custom egg count $\times$ price simulator) and 28-day viability curves.
* **IoT Edge Stations**: Real-time device telemetry, heartbeat monitor, conveyor calibration parameters ($\Delta t = D/v$), and remote station ping.
* **Resilient Offline / Mock Fallback**: If the central backend server is offline, the dashboard automatically serves mock data for seamless development and demonstrations.

---

## 🛠️ Development & Build

### 1. Install Dependencies
```bash
npm install
```

### 2. Start Development Server
```bash
npm run dev
# Running at http://localhost:5173
```

### 3. Build Production Bundle
```bash
npm run build
```

### 4. Run via Docker
```bash
docker build -t ovalens-dashboard .
docker run -p 3000:80 ovalens-dashboard
```
