# Edge operator interface

Batch setup uses Existing batch, New batch and Complete details in one native
dialog. Keep Save/Use and Cancel fixed below a scrollable form at 1024×720.
Use plain labels, generated display codes and only the three Itik Pinas breeds.
Separate original incubation inventory and actual set date from this run's target;
never prefill either from scan counts or an assumed Day 10 date. Cached batches
remain selectable offline. Show local/synced/conflict states and preserve entered
fields during remote refresh. Saving activates a batch only after local commit,
with no motion. STOP cancels late activation while retaining the saved record.

Mode: **Operate**. The operator needs to see the egg, understand why the conveyor
is stopped, and act safely. Foundation University maroon, green, red and slate
are binding. Segoe UI is the native Windows typeface; labels use 12–14 px and
counts use 20 px. Camera controls retain native driver terminology and readback.

The camera well is the primary workspace. Its cycle message stays above the
image. A single side panel groups the latest classification, aligned batch
counts and recent events with spacing and thin dividers. Counts are rows rather
than coloured metric cards. The empty camera well explains setup directly.

Daily operation uses Batch setup, empty-conveyor confirmation, Prepare station,
then a separate Start sorting action. Camera preview and passive software/storage
checks start on opening; serial discovery waits for explicit empty-rig preparation.
Show an inline scrollable readiness checklist in the idle right panel, retaining
the camera preview and fixed STOP/footer controls at 1024×720. Backend offline is
a warning; local storage, model and controller faults block Start. Preparation
never starts a session or releases the belt. Final Start rechecks fresh status
and storage in the background without discovery or preset replay. Settings,
camera/control changes, resets, position changes and STOP invalidate preparation;
readiness is session-only and requires explicit reinspection after a fault.
The cycle heading gives a short feeding instruction, with an explanation below.
Only a clear gate invites the next egg. Completed batches show totals and a
Start next batch action inline. Tools groups Single scan, Settings and camera
retry. Keep the inspection checkbox reachable before every batch.

Maroon identifies primary actions. Green identifies fertile results, amber
identifies penoy/review information and red identifies stop actions. Secondary
commands use neutral surfaces. Status always includes text; colour alone carries
no instruction. Use plain command labels instead of decorative emoji, gradients,
glow, fake instruments or ornamental animation.

The footer reserves space for STOP and session controls at 1024×720. Review
choices appear only when needed. History remains reachable while a review takes
space from the event area. Settings are grouped by Connections, Camera, Detection
and Calibration. No physical operation is implied by preview or a saved default.

Keep latest-only camera buffering, single scheduled inference, background I/O,
and cached widget refreshes. Do not add timers, animation or image assets for
decoration. Inspect normal and minimum window sizes, idle and review states, plus
settings; test long result labels and safety-control visibility.

Idle Camera controls replaces the right record panel while retaining the main
preview and STOP. Automatic modes sit beside their paired manual fields in the
scrollable body. Apply now, Save as default, Load saved settings and Done stay
reachable at minimum size. Sliders pair with exact numeric values and editable
Range fields; spans are explicitly not camera-reported limits. Use native units
and textual driver readback. Camera and Cradle sections share the same panel.
Cradle uses one path confirmation, explicit connection and discrete short
Forward/Backward moves; keep STOP visible throughout. Sorting, scans and batch changes wait until Done;
camera work runs in the background. Do not add a second camera stream or live AI
to this panel. Blank preferences leave the current hardware value unchanged.

Camera edits update the preview live with bounded latest-value coalescing. Keep
sliders editable during camera I/O; suppress stale completion writes to the form.
Explicit save remains separate. Stop, cradle operations and closing cancel
scheduled edits; completion must not restart camera work during those operations.
Live preview avoids restarting the frame-discard period on every slider update;
sorting retains its stopped evidence capture and settling rules.

The footer's neutral Turn light on/off control stays beside STOP and remains
reachable during camera tuning. Its action follows confirmed lamp telemetry;
pending requests show Switching light and disable competing operation starts.
Automatic sorting displays the lamp state with manual changes disabled. Keep
serial work and manual watchdog renewal off the Tk thread.

During a three-board run, show a neutral Pause button beside STOP. Pending pause
and resume requests disable the button and name the action. The paused state
offers Resume while retaining the current session and counters; the main cue
says scans are saved and eggs must stay in place. Keep STOP and Stop sorting
available. A pause completes current motion and classification before holding;
never present an unconfirmed hold as Paused. Camera and manual light controls
remain locked until the session ends. Cache button updates with the other footer
controls and preserve their visibility at 1024 by 720.
