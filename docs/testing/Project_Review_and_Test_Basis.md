# OvaLens Project Review and Black Box Test Basis

These are background notes for the earlier [detailed plan](archive/OvaLens_Detailed_Black_Box_Test_Plan.md). Use the [simplified 30-test form](OvaLens_Black_Box_Test_Plan_and_Template.md) for the current testing template.

**Review date:** 30 October 2026  
**Purpose:** Explain the coverage and unresolved decisions behind [the proposed testing plan](OvaLens_Black_Box_Test_Plan_and_Template.md).  
**Related project documentation:** `TASK-DOC-01` in `PROJECT_PLAN.md`. No feature-completion or test-execution status is changed by this review.

## 1 Review scope and confidence

The review covered the four active subsystems and their integration surfaces: edge startup/operator controls and tests, unified and legacy controller layouts, FastAPI routes/schemas/business services, dashboard routing/pages/API calls, offline storage/synchronization contracts, project planning, and manuscript scope/objectives. The source review informed the cases; it was not a complete security audit, line-by-line certification of every file, or physical validation of the rig.

Existing uncommitted unified-controller work was included as the current intended direction. Source presence and automated tests are evidence of implemented intent, not proof that a physical feature works. The draft therefore keeps every test unexecuted and asks evaluators to record the exact build and installed firmware.

The reference Google document was fetched through the connected Google Drive plugin. It is a CacaoDx form organized around mobile, administrative web, and role-specific workflows. Its testing subject, roles, and results are not applicable to OvaLens.

## 2 Assessment of the supplied reference

Useful features to retain:

- Stable case identifiers and recognizable module/function names.
- User-visible scenarios with procedural steps and expected outcomes.
- Named tester and execution date.
- Grouping by the interface and user role being evaluated.

Changes needed for OvaLens:

- Replace the single Pass/checkmark column with Pass, Fail, Blocked, Not Executed, and approved Not Applicable states.
- Record what actually happened, with screenshot/export/video references and egg/scan IDs. An expected result is not an actual result.
- Complete missing/ambiguous expected outcomes and avoid duplicate scenarios with no distinct coverage purpose.
- Include negative inputs, exact boundaries, stop/restart transitions, offline recovery, and wrong-controller cases.
- Identify hardware, firmware, model, threshold, calibration, operator and batch prerequisites.
- Record defect correction and retests without erasing failures.
- Separate UI functionality from classification accuracy, physical routing, and throughput trials.

The reference's pass-column markers are not copied. No result is inferred from them.

## 3 Why the proposed structure fits this project

The primary deliverable is a test plan plus reusable execution forms and a case catalogue. It can support a manuscript appendix, a witnessed demonstration, and later retesting. It has 72 functional definitions and eight quantitative procedures; the final count of executions depends on variants, repeats, exclusions and the approved sample plan.

The catalogue covers operational and management tasks separately so an agriculture evaluator is not expected to construct HTTP requests. API cases remain externally observable black-box checks performed by a technical evaluator. Source-level checks such as inspecting WAL configuration, counting warmup calls, or reading interrupt implementation belong to engineering verification, not the end user's acceptance checklist.

The measurement procedures follow the current Chapter 1 objectives: binary Day 10 classification, performance by genetic group/batch, physical sorting and cradle association, successful cycles, manual-review frequency, end-to-end time, and throughput. These research outcomes require raw trial evidence in addition to functional verdicts.

## 4 Source to coverage mapping

Paths below are relative to the monorepo root. They identify the reviewed test basis and help maintain the instrument when the project changes.

| Source area | Observed surface or contract | Testing consequence |
| --- | --- | --- |
| `AGENTS.md` | Standalone FastAPI/PostgreSQL authority; local-first edge; Day 10; two biological classes; review workflow; threshold rules | Preserve scope and test offline behavior, identity retention, class handling and review decisions. Do not add Firebase/Hatchio workflows. |
| `PROJECT_PLAN.md` | Existing documentation task and completed batch creation, session sync, image sync, 0.70 automatic confidence, stopped-capture and three-board work | Trace cases to the actual workflows rather than treating the older directory summary as an exhaustive feature list. Unified migration is current local work. |
| `docs/manuscript/01_Chapter_1_Introduction.md` | Four research questions, six objectives, three Itik Pinas groups, Day 10 only, 200 ms Raspberry Pi inference target | EV01–EV07 measure the stated objectives; later hatch administration does not broaden the vision model scope. |
| `edge/launcher.py` | Explicit simulation flag, startup configuration, camera/model setup, workers and shutdown cleanup | SE01/SE03/SE04 distinguish real operation from preview/simulation; SY08 covers restart and retained evidence. |
| `edge/src/ui/app.py`, `batch_setup.py`, `guided_setup.py`, `station_settings.py`, `camera_controls.py` | Operator selection, batch creation/selection, preparation, settings, capture/review, pause/stop, history, local export and run summaries | BA01–BA06, SE01–SE08, SO01–SO12, DA05/DA08/DA10 cover visible workflows and controls. |
| `edge/src/core/batches.py`, `operator_flow.py`, `readiness.py` | Batch metadata validation, original inventory distinct from run target, model/camera/storage readiness and preparation fingerprint | BA03–BA05 exercise input ranges; SE03–SE07 and SY07 exercise invalidated/missing prerequisites. |
| `edge/src/core/settings.py`, `sorting_cycle.py`, `three_board_cycle.py`, `inference.py`, `inference_worker.py` | Saved automatic threshold, stable fresh-frame evidence, manual diagnostic threshold, stopped capture, hold/review and gate positioning | SO03–SO09 and the boundary table distinguish detection, diagnostic and automatic-routing decisions. |
| `edge/src/iot/unified_board.py`, `edge/src/core/station.py` | Unified controller profile, shared single serial link, identity discovery and readiness | SE02 and SY08 verify correct controller selection, disconnection behavior and explicit recovery. |
| `firmware/unified_ovalens/unified_ovalens.ino`, `protocol.h` | Unified stepper/gate/IR/lamp pins; command identification; startup fault; 40 ms detection, 350 ms clearance, 600 ms lockout, 3000 ms link timeout | Record the installed build; test visible holds/faults and physical timing using suitable external tools. Do not assume source constants prove real timing. |
| `firmware/unified_test/unified_test.ino`, `scripts/test_unified_hardware.py` | Numeric-menu component diagnostics on one controller | Useful preparation evidence, but separate from production integrated sorting. No script was run or firmware flashed for this draft. |
| `edge/src/db/local_db.py`, `edge/src/sync/sync_worker.py` and their integration tests | Local sessions/scans, pending metadata/images, acknowledgement/retry and restart recovery contracts | SY01–SY08 and EV08 compare externally visible exports and central records by identity. No internal SQL inspection is required of user evaluators. |
| `backend/app/api/v1/endpoints/` and `api/deps.py` | Auth, users, operators, devices, batches, sessions, scans, analytics, reports, audit logs, settings and backup routes; API-key and role checks | AU/AD/IF cases cover actual published boundaries, including server-side mutation checks rather than only hidden controls. |
| `backend/app/schemas/batch.py`, `scan.py`, `settings.py`, `services/batch_service.py`, `scan_service.py` | Request validation, batch identity conflicts, scan idempotency, historical override and aggregate updates | BA07, SY04/SY06, DA06 and IF01–IF06 exercise valid/invalid requests and stable identities. |
| `backend/app/services/scan_metrics.py`, `core/session_metrics.py`, `edge/src/core/session_metrics.py`, `dashboard/src/utils/sessionMetrics.ts` | Review is a subset of binary classifications; duration/rate require valid session evidence | DA07/DA10 and EV04/EV05 use explicit denominators and distinguish current review counts from referral-event rates. |
| `backend/app/services/report_service.py`, `backup_service.py`, `scan_images.py` | CSV/PDF outputs, selected-field JSON snapshots and stored scan images | DA05/DA08/DA09/AD07 verify actual output contents; snapshot download is not called complete recovery. |
| `dashboard/src/App.tsx`, `components/RoleProtectedRoute.tsx`, `api/client.ts` | Protected layout, role routes, API authentication and expiration behavior | AU01–AU06 and IF05 cover browser and server behavior separately. |
| `dashboard/src/pages/` | Overview, batches, scan explorer, analytics, devices, users, and facility/account/backup/preferences settings | DA, AD, DV and LC cases cover working surfaces, device monitoring/calibration, and administrative follow-up. |
| `dashboard/src/components/HumanInTheLoopOverrideModal.tsx`, `FinalizeHatchModal.tsx`, report/forecast components | Historical scan correction, hatch recording, PDF certificate/report and forecasts | Distinguish historical corrections and projections from physical rerouting and observed hatch results. |
| `edge/tests/`, `backend/tests/test_api.py`, `dashboard/tests/` | Existing regression tests cover many readiness, sync, control and record contracts | Useful engineering evidence remains separate from external user acceptance and witnessed physical trials. Test-file presence is not a new passing result. |

## 5 Decisions and discrepancies to resolve

### Unified controller migration

The selected user scope is the new unified single ESP32 setup. The edge configuration calls this `unified_v4`; the production firmware identifies `UNIFIED_V3:PROTOCOL=3`. These identifiers name different version surfaces, so record both rather than silently normalizing them. Also distinguish production firmware from the separate numeric-menu test sketch. Some existing documentation and tests still discuss dual/three-board rigs.

The inspected discovery code accepts a `CONVEYOR` response as well as unified identity conditions. This makes a wrong-controller/incompatible-firmware negative test particularly useful. This source observation is a reason to test SE02; it is not a demonstrated physical failure.

### Latency target conflict

Current Chapter 1 and `TASK-AI-LAT-01` use a target of no more than 200 ms per image on the Raspberry Pi. Older guidance in `AGENTS.md`'s performance-skill summary names 35 ms. Neither number is a complete mechanical egg-cycle limit. The draft uses 200 ms provisionally because it is stated in the current research scope, and asks the adviser/team to approve a single criterion and statistic before formal acceptance.

### Three different confidence settings

The automatic-sort default/minimum is 0.70, configurable through saved station settings up to 0.99. Automatic evidence must meet that saved value, not merely the minimum. Manual diagnostic routing uses a separate 0.75 review threshold. Detection filtering is another setting and can prevent a prediction from reaching later routing evaluation.

The dashboard facility configuration also has a `confidence_threshold` field. Its presence does not demonstrate that changing it updates the desktop's saved `sort_confidence`. Do not use one as the other's oracle without verifying and approving the synchronization contract.

### Day 10 scope and older wording

Some backlog descriptions still mention other days, while the supplied architectural rulebook and current Chapter 1 limit the vision evaluation to Day 10. Apply Day 10 consistently. Administrative batch/hatch milestones and actual hatch counts can be evaluated without claiming a model for those later incubation stages.

### Existing results are not fresh trial evidence

The current Chapter 4 includes numeric model metrics, latency figures, simulated mechanism results, and economic examples. This review did not establish their supporting raw datasets, trial records, or physical test provenance. Do not carry them into the new forms as measured results. The new campaign needs its own evidence, and any reused historical result needs traceable validation and correct labeling.

### Review metrics and physical confirmation

Stored class totals are binary, with manual review counted as a subset. Historical overrides can update the current class/action and review totals. A review-referral rate for research therefore needs the trial ledger or preserved event evidence, not just a final dashboard screenshot.

The current routing code records a `PASSAGE_ESTIMATED` stage after commanded travel and gate reset. That does not independently sense tray arrival. Observe the actual egg/tray to establish physical routing and drain success.

### Snapshot and reporting scope

The backup service exports selected record fields as JSON/gzip. Its inspected account snapshot omits password hashes, and scan photos are not embedded in those record fields. A successful download does not prove full-fidelity recovery of credentials, every field, or images. Do not add a dashboard Restore success case where no restore operation was identified.

The identified report export formats are CSV and PDF. Do not copy CacaoDx's Excel-export requirement into OvaLens unless that capability is actually adopted. Local filtered exports and backend batch exports have different scopes.

### Read permissions and API checks

Mutation routes provide explicit role/API-key contracts. Several inspected analytics/history/report read routes do not declare the same user dependency as protected mutation routes. Decide whether reads are intended to be public within the deployment or require authenticated access before making an all-data-private acceptance claim. The draft's IF04/IF05 assert the explicit protected-write rules; they do not certify a comprehensive security assessment.

### Unapproved metrics and participant requirements

No verified Foundation University requirement for a fixed black-box case count, respondent count, or exact signature panel was identified in this review. The recommended roles are intended users, a qualified agricultural/hatchery validator, a client/manager representative where applicable, and a technical evaluator, with adviser review according to local requirements. These are recommendations, not claimed institutional mandates.

No new 95%, 99%, or eggs-per-minute success threshold is invented. Agree these values, sample sizes, class/breed representation, confidence interval method and observation period before collecting final trial data.

## 6 Additional depth for the approved scope

The main catalogue includes device monitoring, diagnostics, lamp control, hatch follow-up, batch removal and usability as DV01–DV02, DG01–DG03, LC01–LC02 and UX01. The following describes possible depth or extensions. Give each additional data variant its own run record; update the approved catalogue count if a new case definition is added.

| Area | Suggested externally observable check |
| --- | --- |
| Device monitoring | Run a real registered station, observe its current heartbeat/model details, then stop heartbeat and verify stale/offline indication after the documented interval. Record the actual refresh/stale policy before judging timing. |
| Device calibration records | Authorized manager saves device calibration metadata, refreshes it, and verifies it is not silently interpreted as permission to move the physical station. |
| Manual diagnostics | Exercise valid stationary manual scans and exact score boundaries around 0.75 through an approved external fixture. Check that invalid capture creates no successful production scan. |
| Lamp protection | On an empty rig, test manual-lamp release, idle shutoff and Stop/disconnect behavior; measure observed timeout and distinguish manual keepalive behavior from automatic operation. |
| Detailed optical timing | Drive the external sensor signal with calibrated equipment around the 40/350/600 ms boundaries. Record tolerance and distinct expected outcomes. Human hand movement cannot certify millisecond boundaries. |
| Hatch records | Record valid/invalid final hatch counts on a designated test batch, compare reconciliation with original inventory and relevant counts, and ensure projections remain distinct from actual hatch results. |
| Batch removal/archive | On disposable test records, exercise allowed cancel/confirm and protection of linked history under the approved archive/delete policy. Do not erase evaluation evidence. |
| Responsive/accessibility use | Complete critical desktop controls at the intended display size, dashboard navigation at agreed browser sizes, keyboard navigation and dialog cancellation, and verify errors/status are understandable without color alone. |
| Public/private reads | After agreeing the deployment access policy, test unauthenticated and expired-session reads of scan photos, history, analytics and reports. |
| UI/API parity | Compare batch validation boundaries between desktop, dashboard and their respective APIs; record contract differences rather than assuming all limits are identical. |

## 7 Suggested next review

1. Have the adviser and hatchery/domain representative review scope, wording and evaluator roles.
2. Freeze the production unified firmware and model to be tested; retain the test sketch only for its separate component purpose.
3. Approve numeric acceptance criteria and a feasible unique-egg/batch sample plan. Resolve the inference target and define pause-inclusive timing.
4. Confirm which listed supporting features and additional variants are in the final acceptance scope, and document any approved exclusions.
5. Transfer the approved forms to the institution's requested Word/Google Docs appendix layout if required, keeping the case IDs and evidence fields.
6. Execute, document defects, retest, and write the results from the completed records. Preserve all unexecuted/blocked outcomes honestly.

## 8 Research references

- [ISTQB Foundation Level syllabus version 4.0.1](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf): black-box techniques and test evidence/reporting.
- [ISTQB Acceptance Testing syllabus](https://istqb.org/wp-content/uploads/2024/11/ISTQB-CT-AcT_Syllabus_v1.0_2019.pdf): measurable criteria and acceptance collaboration.
- [Agile Alliance acceptance testing guidance](https://agilealliance.org/glossary/acceptance-testing/): involvement of customers/domain experts in behavior-focused acceptance tests.
- [Northern Arizona University GNAT capstone test plan](https://sce.nau.edu/capstone/projects/CSE/1997/ussoftware/docs/testplan.html): a historical example of explicit black-box inputs and boundary groups, not a required modern template.
- [University of Colorado software testing lecture](https://home.cs.colorado.edu/~kena/classes/5828/s09/lectures/19-testing.pdf): external input/output comparison and the distinction between verification and validation.
