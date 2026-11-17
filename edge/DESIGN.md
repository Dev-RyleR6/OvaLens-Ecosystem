---
name: OvaLens Edge operator interface
description: Restrained Foundation University dim slate workspace for safe native station operation.
colors:
  primary-maroon: "#800000"
  dark-maroon: "#5C0000"
  fertile-green: "#357a38"
  reject-red: "#DC2626"
  review-amber: "#875A12"
  workspace: "#0F172A"
  panel: "#1E293B"
  panel-alt: "#29384D"
  panel-accent: "#374B65"
  border: "#475569"
  border-control: "#94A3B8"
  selection: "#41546F"
  selection-hover: "#3B506C"
  ink: "#F1F5F9"
  ink-secondary: "#D5DEE9"
  ink-muted: "#C3CFDF"
  input: "#111D2E"
  focus: "#F4B2BF"
  brand-text: "#F4B2BF"
  action-text: "#FFFFFF"
  viewport: "#111317"
  viewport-text: "#F1F5F9"
  viewport-muted: "#CBD5E1"
typography:
  body:
    fontFamily: "Inter"
    fontSize: "14px"
  label:
    fontFamily: "Inter"
    fontSize: "13px"
  caption:
    fontFamily: "Inter"
    fontSize: "13px"
  control:
    fontFamily: "Inter"
    fontSize: "14px"
  heading:
    fontFamily: "Inter"
    fontSize: "20px"
    fontWeight: 700
  metric:
    fontFamily: "Inter"
    fontSize: "24px"
rounded:
  main-panel: "8px"
spacing:
  workspace-margin: "20px"
  panel-gap: "16px"
components:
  button-primary:
    backgroundColor: "{colors.primary-maroon}"
    textColor: "{colors.action-text}"
    rounded: "{rounded.main-panel}"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.panel-alt}"
    textColor: "{colors.ink}"
    rounded: "{rounded.main-panel}"
    height: "36px"
  station-field:
    backgroundColor: "{colors.input}"
    textColor: "{colors.ink}"
    rounded: "{rounded.main-panel}"
    width: "150px"
    height: "36px"
---

# Edge operator interface

## Overview

Mode: **Operate**. Extend the established Foundation University workspace with
low-glare dim slate surfaces, a larger camera workspace and task-grouped settings.
The operator must see the egg, understand a stopped conveyor and act safely.
This is the native Edge desktop system; dashboard composition does not govern it.

## Colors

Maroon anchors primary actions. Pale rose marks keyboard focus and brand text. Green, amber and red carry
result and safety meaning with accompanying text. Light ink supports the dim slate
workspace; separate light text serves the dark camera well. The frontmatter
records the shared values from `src/ui/theme.py` and `assets/desktop_theme.json`.

## Typography

Use bundled static Inter regular and bold. Keep native camera terminology and
readback legible. The established font sizes and platform fallback behavior are
specified with the component guidance below.

## Layout

The main workspace has a horizontal margin (20px), vertical margin (16px) and
panel gap (16px). Give available width to the camera; the record panel remains
compact (360px). Station settings uses a persistent left navigation (164px) and
scrollable task forms. Keep its aligned numeric fields (150px by 36px), wrapped
help and driver readback in the form flow. Driver readback scrolls with the
Camera fields rather than consuming a fixed area beneath them.

## Elevation & Depth

Use flat tonal surfaces and thin borders for hierarchy. Do not add shadows or
decorative animation.

## Shapes

Main camera and record panels and the settings workspace use gently curved
corners (8px). Preserve existing component-specific radii rather than applying
one radius indiscriminately to every native control.

## Components

### Established operation and safety guidance

Batch setup uses Choose batch and Create batch in one native
dialog. Keep Save/Use and Cancel fixed below a scrollable form at 1024Ã—720.
Use plain labels, generated display codes and only the three Itik Pinas breeds.
Separate original incubation inventory and actual set date from this run's target;
never prefill either from scan counts or an assumed Day 10 date. Cached batches
remain selectable offline. Show local/synced/conflict states and preserve entered
fields during remote refresh. Saving activates a batch only after local commit,
with no motion. STOP cancels late activation while retaining the saved record.

Mode: **Operate**. The operator needs to see the egg, understand why the conveyor
is stopped, and act safely. Foundation University maroon, green, red and slate
are binding. Use the bundled static Inter regular/bold family for explicit
labels and native control defaults. Body and controls use 14 px, labels use 13 px,
shared captions 13 px and counts 24 px. Existing local metadata may use 12 px. Segoe UI (Windows) and DejaVu Sans
(Linux) are logged fallbacks. Camera controls retain native terminology/readback.

The camera well is the primary workspace. Its cycle message stays above the
image. A single side panel groups the latest classification, aligned batch
counts and recent events with spacing and thin dividers. Counts are rows rather
than coloured metric cards. The empty camera well explains setup directly.

Use the FU dim slate desktop palette: workspace #0F172A, panel #1E293B, borders
#475569 and maroon #800000. The camera well stays dark with separate light text
tokens. Inter, quiet tinted result surfaces and generous spacing provide
the low-glare desktop character; avoid shadows, image assets and decorative timers.
One header batch control includes registered operator context. Settings, More and window
controls live in the header. The bottom action bar reserves a stable right-hand
position for STOP; a single compact strip above it shows sorter, sync and camera
status. The footer carries a concise three-step next-action cue matching the cycle heading.
Control borders use #94A3B8 rather than the structural divider color. Input
placeholders remain readable; keyboard focus uses the FU pale rose border. Slate
selected tabs keep light text in their hover state. Neutral dropdowns use a slate
arrow surface so their light chevron remains visible. Fonts register once for the
process; no runtime download, system font install or decoration timer is needed.

Selectors use `SelectField`: a read-only native ttk.Combobox in the CTk layout,
with dark inset fields, light values/arrows, a pale rose focus border and an eight-row
scrolling popup. All selectors share that treatment, including rig profiles and
history filters; maroon fills identify actions rather than selection fields.
Programmatic changes and linked StringVar writes never invoke a user callback.
Closed-field wheel input scrolls the form without changing a selection; popup
wheel input scrolls only the popup. Native arrows, Enter and Escape handle
selection, and scan/stop letter shortcuts do not run while a picker has focus.

Header context uses three aligned grid columns. Pause belongs beside the sorting
action; manual light control sits near STOP on the right. More opens beneath its
header control. Station settings is centered and clamped to the current workspace,
with responsive help wrapping, persistent left section navigation and fixed actions below its scrollable forms. Camera
auto/manual pairs share an inset group; blank numeric inputs use shared helper
text. Status/result groups expand to fit wrapped messages instead of fixed-height
text clipping. Keep panel separators quiet and selector boundaries distinct.

Daily operation uses Batch setup, empty-conveyor confirmation, Prepare station,
then a separate Start sorting action. Camera preview and passive software/storage
checks start on opening; serial discovery waits for explicit empty-rig preparation.
Show a compact readiness summary in the idle right panel, with Show details
expanding the full scrollable checklist in that panel. Collapse restores run
counts and recent activity. Blocking errors remain named in the compact summary;
offline sync is explicitly non-blocking. Retain
the camera preview and fixed STOP/footer controls at 1024Ã—720. Backend offline is
a warning; local storage, model and controller faults block Start. Preparation
never starts a session or releases the belt. Final Start rechecks fresh status
and storage in the background without discovery or preset replay. Settings,
camera/control changes, resets, position changes and STOP invalidate preparation;
readiness is session-only and requires explicit reinspection after a fault.
The cycle heading gives a short feeding instruction, with an explanation below.
Only a clear gate invites the next egg. Completed batches show totals and a
Start next batch action inline. More groups Single scan and camera
retry. Keep the inspection checkbox reachable before every batch.

Maroon identifies primary actions. Green identifies fertile results, amber
identifies penoy/review information and red identifies stop actions. Secondary
commands use neutral surfaces. Status always includes text; colour alone carries
no instruction. Use plain command labels instead of decorative emoji, gradients,
glow, fake instruments or ornamental animation.

The footer reserves space for STOP and session controls at 1024Ã—720. Review
choices appear only when needed. History remains reachable while a review takes
space from the event area. Settings are grouped by Connections, Camera, Detection,
Calibration and Maintenance. Maintenance contains physical tests and alignment
commands, separated from configuration fields. No physical operation is implied by preview or a saved default.

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


### Station settings navigation and actions

Connections, Camera, Detection, Calibration and Maintenance remain visible in the
left navigation while one scrollable section occupies the content area. Use a
quiet selected surface with pale rose brand text; hover and selection must retain readable
contrast. Configuration values and physical commands have distinct task groups.
The fixed actions are Apply for this run, Save defaults, Load saved, Done and
STOP. Applying affects the current run; saving also remembers defaults. Neither
implies that a physical operation occurred. Camera controls beside the preview
retain their separate Apply now, Save as default and Load saved settings labels.

### Keyboard operation

Shared button keyboard support enables Tab traversal, a visible pale rose focus
border, and Enter or Space activation with the disabled-state guard retained.
Space activation must not propagate into the scan shortcut. Reveal focused
controls inside scrollable forms without switching sections. Entry focus uses a
pale rose border while preserving validation feedback on blur.

### Readable controls, flow and dialogs

Primary and safety action buttons have a minimum height of 44px; auxiliary
buttons have a minimum height of 36px. Settings section navigation is 40px.
Keyboard focus changes the CTk border to the focus token at 2px and restores it
on blur. Never use a Canvas highlight rectangle that squares rounded buttons.
Buttons and checkboxes support Tab, Space and Enter with disabled guards.
Space activation does not propagate into the global scan shortcut. Escape calls
the native WM_DELETE_WINDOW handler, preserving cancellation and close guards.

Settings is directly available in the header; More contains diagnostics.
The READY heading follows actual batch/operator/preparation state: set up a run,
inspect the empty station, then ready to start sorting. The footer presents the
same three-step next action. Diagnostic-only readiness names the single scan.
Feed an egg only when the clear gate cue invites it.

Run quantity remains editable for saved and new batches and pinned with setup
actions. Operator and batch fields scroll above it. Preserve entered values and
local-first activation semantics. Choose batch and Create batch are the current
setup modes.

Dialogs are centered and clamped to the available workspace. The shared minimum
width is 640px, or 880px for requested widths of at least 900px, clamped to available
space. Settings requests 1000 by 800px with a workspace-clamped minimum of 800 by
640px. Startup is separate: 720 by 520px, minimum 600 by 440px. Long forms scroll
above fixed actions in setup, preparation, guide, end-session and batch summary.
History uses the wider dialog treatment. STOP remains reachable in guide,
history, end-session, exit and settings dialogs and the main workspace.

This correction changes presentation and clarity. Preserve background hardware
I/O, latest-only camera buffering and the single camera stream.
## Do's and Don'ts

- **Do** keep camera evidence, cycle instructions and STOP visible at the minimum workspace size.
- **Do** group configuration by operator task and place physical station tests in Maintenance.
- **Do** pair status colors with explicit text and keep driver readback reachable by scrolling.
- **Don't** equate preview, saved defaults or an unconfirmed hardware request with physical readiness.
- **Don't** add decorative timers, image assets, shadows or additional camera streams.
