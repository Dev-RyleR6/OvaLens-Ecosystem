# OvaLens Position-Based Conveyor Operation Prompt

> Historical sensorless specification. For the two-board rig with chamber IR, [Edge Station Control](OVALENS_EDGE_STATION_CONTROL.md) supersedes the sensorless assumptions and startup workflow below. Physical wiring, firmware upload and rig validation remain required.

Update the OvaLens Edge application to support automated duck egg candling and sorting using two wired ESP32 boards (stepper and servo), position-based conveyor movement, spaced conveyor holders, and camera-only egg detection.

Task: `TASK-NEW-EDGE-POS-SPEC-01` (specification and database audit).

Status: software design prepared; hardware integration requires the deployed Arduino sketches and measured holder geometry. The implementation contract below takes precedence wherever an earlier section is ambiguous.

## Objective

When the application starts, show a batch configuration screen before opening the operator dashboard.

The operator must configure:

- Batch code, generated automatically if empty
- Duck breed/genetic line
- Total egg count for the batch
- Operator name
- Separate stepper and servo serial/COM ports
- Conveyor control mode
- Home, chamber, and sorter positions
- Stabilization time
- Classification duration
- Servo timing
- Confidence threshold

Before starting the batch, validate:

- Camera connection
- AI model readiness
- ESP32 serial connection
- Conveyor communication
- Servo communication
- Camera visibility of the chamber

Do not start the conveyor until the operator confirms the configuration.

## Hardware Limitation

There is no physical egg sensor.

The stepper ESP32 controls conveyor motion; the servo ESP32 controls sorting. Confirm candling-light wiring from the deployed sketches before assigning its controller. Do not rely on:

```text
EVENT:EGG_DETECTED
EVENT:EGG_AT_CHAMBER
```

Egg presence must be detected using the camera.

The system must use position-based conveyor movement:

```text
HOME_POSITION
CHAMBER_POSITION
SORTER_POSITION
```

Position control should use the best available method:

1. Step count for a stepper motor
2. Encoder count if an encoder is available
3. Calibrated movement duration for a DC motor as a temporary fallback

A timed DC motor must be clearly marked as prototype mode because belt speed can change due to load, voltage, friction, and egg weight.

## Position Calibration

Add a calibration screen that allows the operator to define:

- Home position
- Chamber position
- Sorter position
- Movement duration or step count between positions
- Conveyor direction
- Motor speed
- Servo angles
- Servo pulse duration

Provide manual controls for:

- Move forward
- Move backward
- Stop conveyor
- Set current position as home
- Set current position as chamber position
- Set current position as sorter position
- Reset servo
- Test fertile route
- Test infertile route

Save calibration values locally and load them when the application starts.

## Operating Mode

Use a conservative one-egg-at-a-time cycle.

Do not pipeline multiple eggs because there is no physical egg sensor or encoder capable of confirming multiple egg positions.

The software queue must have a maximum depth of one egg:

```text
move one egg to chamber
detect egg using camera
classify egg
move egg to sorter
activate servo
verify chamber is clear
start next cycle
```

## Position-Based Cycle

For each egg:

1. Move the conveyor to `CHAMBER_POSITION`.
2. Stop the conveyor.
3. Wait for the camera image to stabilize.
4. Analyze the chamber region of interest.
5. Confirm that an egg is present.
6. If no egg is detected, perform a limited number of positioning retries.
7. If retries fail, stop safely and display `POSITIONING_ERROR`.
8. Turn on the candling light.
9. Wait for the configured stabilization period.
10. Capture multiple frames.
11. Run the vision model.
12. Require a stable classification for 1 to 2 seconds.
13. Apply the confidence rule:
    - Confidence `>= 0.75`: accept `FERTILE` or `INFERTILE`.
    - Confidence `< 0.75`: use `MANUAL_REVIEW`.
    - Camera failure or inference timeout: use `MANUAL_REVIEW`.
14. Save the scan locally to SQLite before moving the conveyor.
15. Display the result to the operator.
16. Move the conveyor from `CHAMBER_POSITION` to `SORTER_POSITION`.
17. Activate the servo according to the result:
    - `FERTILE`: allow the egg to pass through the fertile lane.
    - `INFERTILE`: activate the reject servo.
    - `MANUAL_REVIEW`: route to a review lane or stop safely if none exists.
18. Reset the servo to its neutral position.
19. Finish the calibrated clearance movement without admitting the next occupied holder to the chamber.
20. Use fresh camera frames to confirm that the chamber is clear before advancing the next holder. If the holder geometry cannot provide this checkpoint, block automatic mode until an alternative contract is validated.
21. Increment the processed egg count.
22. Repeat until the target batch count is reached.

## Camera Egg Detection

Create a separate camera presence detector. Do not use the fertility classifier to determine whether an egg exists.

The chamber detector must return:

```text
EGG_ABSENT
EGG_POSITIONING
EGG_PRESENT
EGG_LOST
```

Use the chamber region of interest to detect:

- Egg-shaped contours
- Valid object area
- Valid aspect ratio
- Brightness and contrast difference
- Stable object position
- Optional YOLO egg-object detection

Require several consecutive frames to agree before returning `EGG_PRESENT`.

The detector must reject:

- Empty chamber
- Partial eggs
- Motion blur
- Unstable objects
- Excessive lighting changes
- Invalid object geometry

Before classification:

```text
EGG_PRESENT must be confirmed
```

After sorting:

```text
EGG_ABSENT must be confirmed
```

Never classify an empty chamber as `INFERTILE`.

## State Machine

Implement the operation using these states:

```text
STANDBY
CALIBRATION
MOVE_TO_CHAMBER
CAMERA_POSITION_CHECK
EGG_ABSENT
EGG_POSITIONING
EGG_PRESENT
STABILIZING
AI_SCAN
DISPLAYING_RESULT
SAVE_SCAN
MOVE_TO_SORTER
ACTUATING_SERVO
CAMERA_CLEAR_CHECK
COMPLETE
MANUAL_REVIEW
POSITIONING_ERROR
MOTOR_TIMEOUT
SERVO_TIMEOUT
JAM_ERROR
EMERGENCY_STOP
```

Every movement must include:

- Target position
- Step count or duration
- Start time
- Maximum timeout
- Completion condition
- Safe failure state

Do not assume that the egg is correctly positioned only because the conveyor completed its movement command.

## Software Queue Record

Track the current egg with:

```text
egg_sequence
scan_id
batch_id
session_id
current_position
state
presence_status
classification
confidence
routing_action
started_at
detected_at
classified_at
sorted_at
inference_latency_ms
movement_duration_ms
error_code
```

The queue must preserve egg order and ensure that each AI result belongs to the correct physical egg.

## Proposed ESP32 Serial Commands

These commands describe required capabilities, not the deployed protocol. Map them to each board only after inspecting its Arduino sketch. Do not transmit this vocabulary to the current rig by assumption.

Support:

```text
CMD:MOTOR:START
CMD:MOTOR:STOP
CMD:MOTOR:MOVE:<duration_or_steps>
CMD:MOTOR:HOME
CMD:LIGHT:<brightness>
CMD:SORT:FERTILE
CMD:SORT:INFERTILE
CMD:SORT:MANUAL_REVIEW
CMD:SERVO:RESET
CMD:PING
CMD:EMERGENCY_STOP
```

Requirements:

- Serial reading runs in a background thread.
- Serial writes are thread-safe.
- The UI thread must never wait for serial communication.
- Critical commands must have acknowledgement timeouts.
- A lost serial connection must enter a safe fault state; a firmware watchdog must independently stop motion when host heartbeats expire. A disconnected cable cannot carry a stop command.
- Emergency stop must immediately stop the motor and reset the servo.
- Mock mode may be retained for development but must be clearly displayed.

## Local Persistence

Before resuming or moving the conveyor after classification:

- Save the scan to SQLite.
- Keep SQLite WAL mode enabled.
- Store the batch ID, session ID, sequence number, class, confidence, action, timestamps, latency, position, and synchronization status.
- Continue operating if the backend is offline.
- Synchronize records in the background when the network returns.
- Keep backend scan ingestion idempotent.

## Batch Completion

When:

```text
processed_count >= target_egg_count
```

the system must:

1. Stop the conveyor.
2. Reset the servo.
3. Return the candling light to idle brightness.
4. Save the completed session.
5. Display:
   - Total processed
   - Fertile count
   - Infertile count
   - Manual review count
   - Positioning errors
   - Motor timeouts
   - Servo errors
   - Average inference latency
   - Unsynced scan count

## Operator Interface

During operation, display:

- Batch code
- Current egg number and target count
- Current state
- Expected conveyor position
- Camera egg-presence status
- Conveyor status
- Servo status
- Classification result
- Confidence score
- Inference latency
- Serial connection status
- Positioning errors
- Manual Stop button
- Emergency Stop button

Disable batch and calibration settings while the operation is running, except for emergency controls.

## Safety Rules

Stop safely when:

- The camera cannot detect an egg at the chamber position
- The camera cannot confirm that the chamber is clear
- The conveyor exceeds its movement timeout
- The servo does not acknowledge completion
- The serial connection is lost
- The expected position and camera result disagree
- The operator presses emergency stop

Never convert camera failure, positioning failure, movement failure, or inference failure into `INFERTILE`.

Use:

```text
MANUAL_REVIEW
POSITIONING_ERROR
MOTOR_TIMEOUT
SERVO_TIMEOUT
JAM_ERROR
```

as appropriate.

## Tests

Add tests for:

1. Batch configuration validation
2. Position calibration
3. Home-to-chamber movement
4. Chamber-to-sorter movement
5. Camera detects an egg
6. Camera detects an empty chamber
7. Unstable egg detection
8. Positioning retry
9. Positioning timeout
10. Normal fertile cycle
11. Normal infertile cycle
12. Low-confidence classification
13. Inference timeout
14. Chamber-clear verification
15. Motor timeout
16. Servo timeout
17. Serial disconnection
18. Emergency stop
19. SQLite persistence before movement
20. Batch completion
21. One-egg-at-a-time ordering

The first implementation must use:

```text
position-based movement
+ camera egg detection
+ camera chamber-clear verification
+ one egg at a time
```

Do not implement multi-egg pipelining until a conveyor encoder or physical egg sensor is installed and validated.

## Confirmed Rig and Implementation Contract

### Hardware and geometry gate

- Confirmed: two ESP32 boards, a stepper conveyor, separate servo, spaced egg holders, no physical egg-presence sensor.
- Port names are configurable and distinct; COM5/COM7 are prototype examples, not fixed device identities.
- Obtain both deployed sketches and document firmware versions, motor driver, direction, stop behavior, telemetry, and light wiring.
- Measure holder pitch, chamber-to-sorter distance, egg envelope, camera ROI, and the travel interval that leaves the chamber empty.
- Maximum one unresolved egg/result association. Other holders may contain eggs, but must not be classified or sorted until the active cycle resolves.
- If the next occupied holder reaches the chamber before the active egg finishes sorting, the simple empty-chamber cycle is not validated. Require wider spacing, empty intervening holders, or separately approved tracking changes. Do not silently add pipelining.
- A reported step count is an estimate of belt displacement, not proof of egg location. Reset, power loss, unexpected movement, or suspected missed steps invalidates the reference.
- Setting home establishes software zero. Without a reference sensor, the operator must physically align a holder and confirm the reference after startup or a position fault.
- Use relative forward distances per cycle, expressed in motor steps. Define chamber and sorter offsets from the aligned holder reference; do not repeatedly command a global belt position that would reverse travel or revisit the same holder.

### Serial and stopping contract

- Maintain independent background workers for both boards. Hardware-free simulation must be explicit; never switch to simulated captures during real operation.
- Negotiate/validate board role and supported commands at startup. Connection success alone is insufficient.
- Each finite move needs a command ID, signed distance and units, speed, monotonic deadline, acceptance reply, completion reply, and reported position/idle state. Reject stale or mismatched replies. If legacy firmware cannot correlate replies, upgrade it or document a validated adapter before automatic mode.
- Distinguish software-reported servo angle from independently measured servo position. Use acknowledgement plus calibrated settling/hold time; describe mechanical delivery as unverified unless separately observed.
- On timeout, do not retry a movement automatically: completion may be uncertain. Positioning retries are allowed only after confirmed stationary state and fresh camera evidence, within configured maximum attempts and total travel.
- STOP must cancel queued/active motion without homing. HOME is a separate deliberate operation. The current prototype STOP-and-home behavior cannot implement emergency stop.
- Each board must handle its own heartbeat expiry and bounded actions. The motor must stop independently if either required board fails or the host stops servicing heartbeats.
- Emergency stop cancels pending actuation and latches a fault. Servo reset must occur only when mechanically safe; agree the safe angle from the rig. Require operator acknowledgement and reference validation before restart. Provide a physical emergency stop independent of Python/USB.

### State transitions and evidence

Normal cycle:

```text
STANDBY -> MOVE_TO_CHAMBER -> CAMERA_POSITION_CHECK
-> STABILIZING -> AI_SCAN -> SAVE_SCAN -> DISPLAYING_RESULT
-> MOVE_TO_SORTER -> ACTUATING_SERVO -> CLEARANCE_MOVE
-> CAMERA_CLEAR_CHECK -> SAVE_CYCLE_COMPLETION
-> COMPLETE (target reached) or MOVE_TO_CHAMBER (next holder)
```

- Presence is an independent detector using ROI geometry and image evidence, never a fertility label. Presence statuses are observations, not biological classes.
- Start with at least 8 distinct fresh observations spanning 1.5 seconds for stable presence/classification; gaps over 0.5 seconds reset confirmation. These are provisional software defaults requiring camera trials.
- Confirm class agreement, stable location, valid geometry, and lighting; use the minimum confidence across the accepted classification window. The configured routing threshold must be in `[0.75, 1.0]`.
- Provide calibrated illumination for presence and clearance checks. After switching candling brightness, restart stabilization and use only frames captured after settling.
- Require at least 5 consecutive distinct fresh empty frames spanning a configurable clearance interval before admitting the next holder. Missing frames, stale frames, and camera errors are not empty evidence.
- Tag all work with cycle ID, holder sequence, inspection generation, and frame timestamp. Ignore late results from a prior cycle or pre-movement capture.
- Unknown classification from camera/inference failure stays unknown and routes to MANUAL_REVIEW; never synthesize INFERTILE. With no validated review lane, stop for operator removal/resolution.
- No egg found is an empty-holder/positioning event, not a completed egg or a fertility scan. Count actual eggs resolved; record empty holders separately. Exhausted retries require intervention.
- Increment completed count only after routing completion evidence, clearance confirmation, and committed cycle completion. Low-confidence scans contribute to review counts rather than accepted/rejected totals. Manual removal needs an explicit operator resolution record.
- Save failures prohibit further movement. Backend unavailability alone does not prevent local operation; data-validation/sync-integrity errors must be shown and affected records retained for reconciliation.
- On restart, unresolved cycles enter RECOVERY_REQUIRED. Do not replay motion or servo commands. Retain IDs, inspect the holder/egg, resolve or abort the cycle, and re-establish position before restarting.

### Persistence and migration plan

See `OVALENS_POSITION_BASED_DATABASE_AUDIT.md` for schema findings and proposed additive migrations. Do not erase databases or normalize historical labels as part of this specification task.

### Additional verification cases

In addition to the tests above, cover two-board identity mismatch, stale acknowledgements, step/duration unit mismatch, STOP without homing, independent firmware watchdog expiry, next-holder intrusion, empty-holder counting, stale frames, lighting transitions, failure after scan commit, restart recovery without motion replay, completion persistence failure, and manual-review records syncing without becoming infertile.

Software verification uses fake clocks, cameras, transports, and temporary SQLite files. Firmware watchdog behavior, physical stopping, geometry, and route delivery require rig tests after the sketches are supplied. Passing software tests does not establish physical sorting accuracy.
