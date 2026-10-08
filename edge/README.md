# OvaLens Edge — Computer Vision Candling & Conveyor Controller

> **Subsystem**: `edge/`  
> **Platform**: Raspberry Pi 5 / Industrial Edge PC / Desktop  
> **License**: Apache License 2.0  

**OvaLens Edge** is an offline-first, real-time computer vision application designed to inspect duck eggs on a motorized conveyor, classify embryonic development using Ultralytics ONNX inference, and control mechanical sorting via ESP32 microcontrollers.

The default detector is now **best_v3.onnx**, exported from the supplied
**best_v3.pt** checkpoint (Ultralytics YOLO26n, two classes, 640px, FP32 input).
The app uses its ONNX export for sorting. Explicit `ONNX_MODEL_PATH` or constructor
paths take priority; installations without the v3 export use `best.onnx`.
The previous export is retained. A present but invalid v3 model blocks automatic
sorting rather than silently loading the previous ONNX. Restart the app to switch
an already-running session. See [model verification](../docs/EDGE_THREE_BOARD_IMPLEMENTATION.md#supplied-best_v3-model).

**Current main launcher status:** New stations default to the three-board handoff rig: conveyor, sensor/servo, and lamp ESP32s. Existing saved two-board settings retain their explicit profile. Sorting requires verified ONNX class metadata, inspection and calibration on each connection/batch. Three-board routing stops at measured gate boundaries; a pause does not consume passage distance. See [three-board setup and verification](../docs/EDGE_THREE_BOARD_IMPLEMENTATION.md) or [existing two-board setup](../docs/OVALENS_EDGE_STATION_CONTROL.md). Firmware compilation and simulations do not establish physical sorting accuracy.

Use **Tools > Single scan** (Space) for a camera diagnostic. It waits for a fresh frame and shows inference/storage progress; timeouts discard late results. **End Session** cancels unfinished predictions and finalizes local records. If finalization fails, **Retry Finalization** preserves the original session. Reaching the diagnostic target stops additional scans until a new batch is configured.

---

## Quick setup

On Windows, double-click **Start_OvaLens.cmd** in the repository root. It uses the
project `.venv` automatically. `python edge/launcher.py` also selects that
environment before importing packages, so the shared `serial` package cannot
mask the project's PySerial. Close and reopen an already-running app after an
environment fix. Check imports without hardware using
`python edge/launcher.py --check-runtime`.

Run `python edge/launcher.py` and enter the batch details. The saved camera starts
its preview automatically. Check the empty conveyor, alignment and gate, tick
the inspection box, then click **Start sorting**. This checks the camera, connects
the boards, prepares the empty station and starts the batch in the background.
**STOP** remains available during preparation. Saved camera controls, timing and
gate calibration are retained. New defaults use **COM5 stepper**, **COM7 servo +
IR**, **COM9 light**, and **camera 0**. Discovery verifies firmware roles if USB
ports change; healthy connections are reused between batches. Install the three
v3 sketches once before connecting. **Tools** contains Single scan, Settings and
Retry camera preview and Camera controls.

Feed one egg only when the large instruction says **Feed next egg**. Wait through
**Inspecting egg**, **Positioning gate** and **Wait — egg passing**. Review choices
appear when needed. At the target, the station finishes the last gate passage,
saves final totals locally and shows **Start next batch** on the same screen.
The three-board result hold defaults to **300ms**; saved custom timings remain
unchanged. Pre-capture settling defaults to 1500ms; evidence checks remain intact.

The camera preview stays on while eggs move. Automatic AI and bounding boxes
start only after the sensor stop is confirmed, the lamp is on, and the 1500ms default
settling period finishes. Three fresh predictions spaced at least 150ms apart
must agree over at least 300ms. The displayed box stays on its captured image;
it clears when movement resumes. Low confidence or disagreement holds the egg
for manual review. **Single Scan** is an explicit diagnostic action and is
blocked when the connected conveyor reports movement.

After classification is saved locally, the sorting servo positions and confirms
completion **before the stepper resumes**. Its angle stays set through the
calibrated gate exit. Feed the next egg when the status says **Feed next egg**;
an earlier arrival holds the rig for inspection to protect the previous egg's route.

## Tune the camera beside its preview

Before starting a session, click **Camera controls** above the preview (also under
**Tools > Camera controls**). The side panel keeps the image visible while you
change autofocus, exposure, gain, white balance, brightness, contrast, saturation
or sharpness. Drag a slider or type an exact value, then Apply. Scroll for
additional controls. **Range** edits a slider's minimum and maximum; these are
editable tuning spans, not hardware-reported limits. Custom spans save with
camera defaults. Turn an automatic mode **Off** to
edit its corresponding manual value; **On** clears that manual preference.

- **Apply to preview** sends the values to the current camera without saving.
- **Save as default** applies and saves them in `edge/db/edge_settings.json`.
- **Load saved settings** fills the form; click Apply to preview to use them.
- **Done** closes the panel and leaves the applied preview settings in place.

Blank numeric values and **Unchanged** leave that camera property untouched;
they do not reset it to its factory value. Values use the camera driver's units,
so supported controls and ranges depend on the webcam. Readback shows verified,
unverified or rejected requests. A verified readback does not establish optical
sharpness: inspect a stationary egg in the preview. Camera tuning is locked
during sessions and scans. Applying changes clears the inspection confirmation;
check the rig again before Start sorting. Preview-only changes remain in memory
until restart; Save as default keeps them for the next launch.

To position a cradle for camera calibration, open the **Cradle** section:

1. Check that the movement path is clear and keep hands away from the mechanism.
2. Tick the path confirmation and click **Connect for alignment**. This opens the
   saved COM5/COM7/COM9 links, acknowledges startup/STOP faults, holds the belt and
   turns on the candling light. Other faults require inspection in Settings.
3. Start with **10** or **25 steps per click**, then click **Forward** or
   **Backward**. Each click makes one slow move and holds again. The IR sensor
   can stop a move early; actual movement and software position appear below.
4. Switch to **Camera**, adjust focus/exposure while stopped, then Save as default.
5. Click **Done** to hold the conveyor and turn the light off. Re-inspect and align
   the empty rig before sorting; normal preparation restores the saved speed.

Jogs are limited to 1000 steps per click and use a 5000us pulse half-period.
Forward follows the configured conveyor direction. No home reference is reset
by these controls. **STOP [R]** cancels motion; reconnect explicitly after
inspection. Automatic scans and sorting stay blocked while this panel is open.

## 🌟 Key Subsystem Features

- **Decoupled Quad-Thread Concurrency**:
  - **Thread 1 (Camera Grabber)**: Continuous background frame consumer with single-frame atomic buffer (DirectShow / V4L2) eliminating video delay.
  - **Thread 2 (Inference Engine)**: Pluggable ONNX Runtime FP16 / PyTorch inference engine with 3-pass warmup and geometric candling heuristics ($0.65 \le \text{AR} \le 1.45$).
  - **Thread 3 (IoT Serial Driver)**: Non-blocking PySerial ESP32 driver with delayed ejection timer calculation ($\Delta t = D/v$).
  - **Thread 4 (Local Storage & Sync)**: SQLite WAL mode persistence with background HTTP REST sync worker (`POST /api/v1/scans/sync`).
- **CustomTkinter 60 FPS Desktop GUI**: Operator interface with real-time HUD, live camera overlay, Day-10 Penoy counter, and manual override triggers (`[SPACEBAR]` and `[R]`).
- **Explicit Simulation**: Synthetic camera preview requires selecting simulation at startup. Camera failure in normal mode reports an error and stops accepting frames.

---

## 📁 Directory Layout

```
edge/
├── models/                       # YOLOv8 weights & ONNX exporter
│   ├── weights/best.onnx         # Current model; inspect actual tensor precision
│   └── export_onnx.py            # Automated export script
├── src/
│   ├── core/
│   │   ├── camera.py             # Thread-safe DirectShow/V4L2 grabber
│   │   ├── heuristics.py         # Optical candling & AR heuristics
│   │   └── inference.py          # ONNX Runtime FP16 inference
│   ├── db/
│   │   └── local_db.py           # SQLite WAL manager
│   ├── iot/
│   │   └── serial_driver.py      # Non-blocking ESP32 PySerial driver
│   ├── sync/
│   │   └── sync_worker.py        # Background HTTP REST sync worker
│   └── ui/
│       ├── app.py                # CustomTkinter 60 FPS operator desktop GUI
│       └── theme.py              # Foundation University brand tokens
├── tests/
│   └── test_edge_pipeline.py     # Automated unit & smoke test suite
├── launcher.py                   # Clean entry point
└── requirements.txt              # Edge Python dependencies
```

---

## ⚙️ Setup & Execution

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment (`edge/.env`)
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

### 3. Run Operator Desktop App
```bash
python launcher.py
```

### 4. Run Automated Tests
```bash
python -m pytest tests/test_edge_pipeline.py -v
```
