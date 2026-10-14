# OvaLens Edge — Computer Vision Candling & Conveyor Controller

## Daily station readiness

1. Open the station. Camera preview and passive configuration, model/warmup and
   local storage checks run in the background. Startup does not connect serial boards.
2. Create/select a complete batch in **Batch setup**, including while offline.
3. Empty and align the conveyor, inspect the gate, tick the confirmation, and
   press **Prepare station**. Remembered ports are tried first (COM5 stepper,
   COM7 gate/IR, COM9 lamp); firmware roles are verified independently of port order.
   Connecting can reset an ESP32 and move its servo. Preparation acknowledges
   inspected faults, establishes the software reference and returns the gate to
   neutral while holding the conveyor. It does not start a session or move the belt.
4. Review the inline checklist, then press **Start sorting**. Final Start checks
   fresh controller STATUS, camera/model, local batch and storage on a worker;
   it does not repeat discovery or calibration. Feed only when instructed.

Readiness is never persisted across launches. Camera/configuration changes,
board resets/disconnection, position changes and STOP invalidate preparation.
Clear the problem, inspect the empty rig and prepare again; reconnecting alone
never resumes sorting. During a run, existing camera/serial/fault checks hold
or stop the cycle and preserve recorded evidence. Pause/Resume remains available.

Offline backend access and pending sync are warnings. Complete local batches
remain usable; known identity/metadata conflicts block that batch until a matching
backend acknowledgement resolves them. Conflict state survives failed retries.
SQLite WAL integrity and real write checks run during startup/preparation; final
Start rechecks writes without repeating the full integrity scan. Image storage
must be writable with at least 256 MiB free. Scans/photos are not erased by checks.
Use **Recheck software** for software/storage problems and **Tools ? Settings**
for advanced configuration; use **Prepare station** to retry controller preparation.

Controller acknowledgements verify communication and reported outputs, not actual
motor travel, servo position or lamp illumination. Physical inspection remains
required; sensor feedback would be needed to prove those actions automatically.


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

Run `python edge/launcher.py`, confirm the operator name and open the station.
The last saved batch/target is restored; use **Batch setup** to create or select
a different batch. The saved camera starts its preview automatically.
Check the empty conveyor, alignment and gate, tick
the inspection box, then click **Prepare station**. This checks the camera and
storage, connects the boards and prepares the empty station in the background.
When readiness passes, press **Start sorting** to begin the batch.
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

Automatic sorting defaults to **0.70 (70%)** confidence. Change it in
**Tools > Settings > Detection > Automatic-sort confidence** (0.70–0.99).
All three stopped-frame predictions must meet the configured threshold and agree;
lower confidence, conflicting evidence or a rig fault still requires review.
Existing saved thresholds are retained unless edited. Manual diagnostic scans
keep their 75% review threshold. Confidence bands in backend history are separate
from the actual sorting/review action.

An off-centre egg can sort automatically: the preview crosshair is an alignment
guide, not a mandatory acceptance zone. A single IR-stopped egg must still have
valid geometry, meet the saved confidence threshold in all three fresh frames,
and retain the same class and stable box position. Multiple eggs, low confidence,
invalid geometry or inconsistent captures require manual review. Restart Edge
when the station is idle after updating; an existing review is not automatically
accepted or released by a code change.

After classification is saved locally, the sorting servo positions and confirms
completion **before the stepper resumes**. Its angle stays set through the
calibrated gate exit. Feed the next egg when the status says **Feed next egg**;
an earlier arrival holds the rig for inspection to protect the previous egg's route.

## Pause and resume sorting

During three-board sorting, use **Pause** beside STOP to take a break without
ending the session. **Pausing...** finishes the current move or egg classification,
saves the scan and positions its gate before holding the conveyor. Wait for
**Sorting paused**, then leave eggs and the cradle in place. The lamp turns off;
the camera preview and background sync continue. **Resume** checks the held
position and egg state, then continues the same session with its saved counts
and photos. A changed position, sensor, gate or disconnected board requires
inspection and recovery instead of resuming. Paused time does not count toward
the no-egg timeout. Finish any manual review before pausing.

Pause/Resume works while the app remains open. **Stop sorting**, **STOP** and
closing the app end or interrupt the run; saved scans and photos remain in local
history. Reopening requires inspecting the interrupted rig rather than automatic
motion recovery. Camera controls and manual light remain locked during a paused
sorting session.

## Tune the camera beside its preview


Before starting a session, click **Camera controls** above the preview (also under
**Tools > Camera controls**). The side panel keeps the image visible while you
change autofocus, exposure, gain, white balance, brightness, contrast, saturation
or sharpness. Sliders and automatic modes update the preview live. Typed values
apply after a short pause. Changes remain temporary until saved. Scroll for
additional controls. **Range** edits a slider's minimum and maximum; these are
editable tuning spans, not hardware-reported limits. Custom spans save with
camera defaults. Turn an automatic mode **Off** to
edit its corresponding manual value; **On** clears that manual preference.

- **Apply now** sends the form immediately, including loaded saved values, without saving.
- **Save as default** applies and saves them in `edge/db/edge_settings.json`.
- **Load saved settings** fills the form; click Apply now to use them.
- **Done** finishes the last valid queued live edit and closes the panel, keeping
  the applied preview settings. Incomplete or invalid edits are not applied.

Blank numeric values and **Unchanged** leave that camera property untouched;
they do not reset it to its factory value. Values use the camera driver's units,
so supported controls and ranges depend on the webcam. Readback shows verified,
unverified or rejected requests. A verified readback does not establish optical
sharpness: inspect a stationary egg in the preview. Camera tuning is locked
during sessions and scans. Applying changes clears the inspection confirmation;
inspect and Prepare station again before Start sorting. Preview-only changes remain in memory
until restart; Save as default keeps them for the next launch.

Live updates combine rapid slider changes into the newest value, with at most
one camera request in flight. Sliders stay responsive while the background
camera worker applies a request. Failed live updates report the error and wait
for another edit or Apply now rather than repeatedly retrying. Switching to
Cradle or pressing STOP cancels scheduled live edits; automatic sorting and
scanning remain blocked while tuning. Camera hardware may take time to settle
after a setting changes. Normal sorting retains its stopped settle and fresh
capture checks.

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

## Manual candling light

Use **Turn light on / Turn light off** beside **STOP [R]**, including while the
Camera controls panel is open. The button updates after the light controller
confirms its state. If the station is disconnected, this action connects only
the saved light port (COM9 by default); it does not connect or move the stepper
or sorting servo. Supported startup/STOP/lamp-timeout faults are acknowledged
only on the light controller by this explicit action.

Manual mode refreshes the light command every five seconds so it remains on
while the application is operating. The firmware's existing 15-second lamp
watchdog and connection watchdog remain enabled. **STOP**, shutdown and starting
station preparation cancel manual control and turn the lamp off. The switch is
disabled during sorting, capture, setup and cradle movement; automatic sorting
retains control of its own lighting. Switch state is not saved across restarts.
Errors appear in Recent activity and, when open, the camera panel.

## Saved scan photos and backend sync

Use **Batch setup > New batch** on Edge. Enter one of the three Itik Pinas breeds,
the incubator, actual incubation set date and original egg count. Enter the scan
target separately under **Day 10 candling run**; it may be smaller than the original
inventory. The operator name is an entered attribution, remembered with the last
selection; it is not a dashboard login. Creating/selecting a batch does not start
motion. The complete batch record and selection are saved locally before sorting.
Each new batch gets a permanent UUID and a generated display code. A later run,
pause/resume or restart keeps that batch identity; another run has its own session.

**Existing batch** includes locally created records and cached active office
batches, including batches marked candling due. It works offline. Batch selection,
breed, incubator, operator and run target are remembered. Original egg count and
set date are never guessed from a target, scan history or the current day.
**Complete details** fills those missing fields for older local batch references,
preserving every original batch, session and scan ID. Resolve/stop the current
session before changing batches. Legacy records retain their old display codes.

The worker first registers complete pending batches at `POST /api/v1/batches/register`
using the station API key, then registers sessions and sends scan records. Batch
registration is idempotent across retries and concurrent requests. ID/code conflicts
with different details show an error and retain the local queue; they never overwrite
the backend's inventory. Batch registration and the SQLite queue survive restarts.
Batch-only records sync even before scanning. API/network failures never block sorting.
The sync badge includes pending batch registrations and session completions.

SQLite remains in WAL mode. Storage operations serialize connection lifetimes
through a per-file thread/process lock (`*.db.lock`) and close each connection
explicitly. Network requests and photo I/O remain outside that lock. This avoids
concurrent writer/checkpoint races on the installed older SQLite runtime; see
[SQLite's WAL-reset bug documentation](https://www.sqlite.org/wal.html).

Signed-in operator accounts may create batches through the existing dashboard API;
editing, stage changes, hatch finalization and deletion retain their manager/admin
permissions. The dedicated Edge route authorizes create/replay only and records the
station and entered operator in a creation audit; it does not impersonate a user.
The dashboard continues to read the central PostgreSQL records. Restart the backend
and Edge after updating; both must use the matching API key and reachable API URL.

After local finalization, the worker queues the original session completion time
in SQLite and sends it to `PUT /api/v1/sessions/<id>/end` once every scan record
has been acknowledged. Failed or lost completion acknowledgements retry across
restart, including older finished local runs. One missing batch cannot starve
other sessions. Photos retry independently. Keep Edge running while its queue
drains; network requests never run on the conveyor or GUI thread.

The dashboard's batch list and open session drawer refresh at the configured
polling interval. Finished candling runs show **Finished** in the session list.
Finishing Day 10 sorting does not mark the 28-day incubation batch as completed;
the incubation batch remains active until its hatch outcome is finalized.

Real automatic scans and manual Single Scan captures save the exact classified
camera snapshot as a quality-95 JPEG beside SQLite, in
`edge/db/local_scans/<scan-id>.jpg`. Preview frames and simulation are not saved.
The disk write runs on the capture/storage worker before the scan is committed;
a failed photo write prevents that capture from being counted or released.

With the backend running and matching `API_KEY` / `API_BASE_URL` settings, uploads
are automatic. The background worker first syncs classification records, then
uploads up to five queued photos per pass to `POST /api/v1/scans/upload-image`.
Network failures retain local photos and their persistent retry state. The sync
pending count includes photos until their scan ID, SHA-256 digest and size have
been acknowledged. Existing locally saved photos are picked up after restart,
including photos whose classification records were synced previously. Historical
records without a saved photo cannot be reconstructed.

Open the dashboard's **Scan Explorer** and select a scan to see its photo and
classification. Restart the Edge app, backend and dashboard dev server after
updating. The backend stores JPEGs in `STORAGE_DIR` (default
`storage/candling_scans`) and serves `/storage/<scan-id>.jpg`; development and
production dashboard proxies forward those requests. Docker uses the persistent
`scan_images` volume. Include both PostgreSQL and this directory/volume in backups.
The API accepts complete JPEGs up to 10 MiB by default
(`MAX_SCAN_IMAGE_BYTES`) and 25 megapixels, preserves original uploaded bytes,
and rejects attempts to replace a scan's photo with different bytes. Local copies
remain on disk after upload; no automatic image cleanup is performed.

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
