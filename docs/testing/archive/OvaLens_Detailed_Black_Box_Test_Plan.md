# OvaLens Black Box Testing Plan and Recording Template

**Foundation University | College of Computer Studies | BS Information Technology**  
**Project:** OvaLens A YOLOv8 Based Deep Learning System for Automated Near Real Time Candling and Sorting of Itik Pinas Duck Eggs  
**Document version:** 0.1 | **Prepared:** 30 October 2026 | **Status:** Draft for adviser and partner hatchery review  
**Documentation context:** `TASK-DOC-01` in `PROJECT_PLAN.md`. This draft does not mark an implementation task or physical acceptance test complete.

## 1 Purpose and scope

This instrument specifies how evaluators will check whether OvaLens produces the required visible results when given normal, invalid, boundary, and interrupted inputs. It covers the desktop operator application, the unified single ESP32 controller, the camera and candling mechanism, local record retention, synchronization, the administrative dashboard, and documented API interfaces.

The evaluator judges screens, downloaded records, documented interface responses, and observed physical egg movement. Source-code inspection and internal database implementation checks are outside the execution of these black-box cases. Reviewing the repository to prepare this instrument does not constitute executing the cases.

The biological scope is **Day 10 Itik Pinas eggs**, representing **IP-Itim, IP-Khaki, and IP-Kayumanggi**. There are two biological classes, **FERTILE** and **INFERTILE**. **MANUAL_REVIEW is a workflow state**, not a third biological class. Hatch completion records are administrative follow-up; they do not extend the vision model to other incubation days.

There are **72 functional case definitions and eight quantitative evaluation procedures**. Some definitions contain several data variants; record each variant separately. Case counts are a proposed coverage plan, not a university-mandated sample size. All results begin as **Not Executed**. No result, signature, accuracy, or timing measurement is supplied by this draft.

## 2 Basis of the instrument

The supplied [CacaoDx reference form](https://docs.google.com/document/d/1cxyTO3B0cykP_3A2Uzg-WYT5wjpAgy82hYFwn63_BOM/edit) provides the useful pattern of case identifiers, module names, procedures, expected results, and tester identification. OvaLens extends it with explicit actual results, execution status, evidence, prerequisites, requirement links, and retesting records.

The test design uses valid and invalid input groups, boundary values, combinations of conditions, and state changes. These are established black-box techniques described in the [ISTQB Foundation Level syllabus, version 4.0.1, section 4.2](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf). Their application here is specific to OvaLens.

Acceptance criteria should be agreed and measurable before execution, following the distinction between requirements, acceptance criteria, and acceptance tests in the [ISTQB Acceptance Testing syllabus, section 1.1.2](https://istqb.org/wp-content/uploads/2024/11/ISTQB-CT-AcT_Syllabus_v1.0_2019.pdf). The templates and signatory recommendations below are project proposals; they do not claim to be an official Foundation University form.

## 3 Evaluators and responsibilities

| Role | Recommended participant | Responsibility and signature meaning |
| --- | --- | --- |
| User evaluator | Intended candling worker or hatchery operator | Performs the operator workflows and attests to the observations recorded for those workflows. |
| Domain validator | Agriculture department representative with poultry or hatchery expertise, experienced candler, or designated hatchery specialist | Establishes the Day 10 labeling guide, validates reference egg labels, observes handling and destination trays, and signs the agricultural evaluation within their expertise. |
| Management evaluator | Hatchery manager or designated client representative | Exercises batch monitoring, reports, and management tasks and states whether the tested workflow meets the partner hatchery's needs. |
| Technical evaluator | Adviser-approved IT evaluator or tester | Executes API, access-control, boundary-fixture, and controlled failure scenarios. Records observations without using internal implementation details as the pass condition. |
| Researchers | OvaLens development team | Prepares equipment and test data, operates agreed test tools, records evidence, fixes defects, and arranges retesting. Distinguishes researcher-run verification from independent user acceptance. |
| Academic reviewer | Capstone adviser or panel representative, when required | Reviews scope, procedure, criteria, and the reported evidence according to the capstone process. This signature does not substitute for actual user testing. |

An intended user and an agriculture specialist are both useful participants. One qualified person may cover more than one role; record that overlap. A department affiliation alone does not establish candling expertise. Record each evaluator's relevant experience. The adviser should confirm the final required signatories and participant count before the formal session.

## 4 Configuration and entry conditions

Complete these fields for every execution campaign. A changed firmware, model, calibration, or software build requires a new campaign identifier or clearly identified retest configuration.

| Field | Value to record |
| --- | --- |
| Campaign ID and location | __________ |
| Dates and time zone | __________; use Asia/Manila or UTC+08:00 consistently |
| Evaluators and roles | __________ |
| Software build | Commit ID: __________; describe any uncommitted changes: __________ |
| Edge host | Actual Raspberry Pi or PC model, OS, RAM, and power supply: __________ |
| Camera | Device identity, resolution, frame rate, exposure and other saved controls: __________ |
| Model | ONNX filename, version or checksum, two-class mapping: __________ |
| Operating mode | Real hardware / simulation / controlled external fixture: __________ |
| Controller profile | Unified single board; edge profile `unified_v4`; selected port: __________ |
| Installed firmware | Filename, build date or checksum, and reported protocol/version: __________ |
| Unified wiring confirmation | IR GPIO26; gate GPIO32; lamp GPIO27; step GPIO16; direction GPIO4; enable GPIO17; deviations: __________ |
| Calibration | Holder spacing, travel to gate, direction, speed, settling time, gate angles, and clearance: __________ |
| Decision settings | Detection threshold: __________; automatic-sort threshold T: __________; manual diagnostic review threshold: 0.75 |
| Backend and dashboard | Build/version, deployment host, browser/version, URL: __________ |
| Test records | Test database or isolated deployment identifier and baseline export: __________ |
| Physical samples | Unique egg IDs, batch IDs, breeds, verified incubation day, and reference labels: __________ |
| Agreed criteria | Approved threshold sheet from section 10 and approval date: __________ |

Before execution:

1. Use a designated test environment and test accounts. Record an initial export or snapshot so new and pre-existing records can be distinguished.
2. Confirm that `firmware/unified_ovalens/unified_ovalens.ino` or the agreed successor production firmware is installed for integrated cases. The numeric-menu `unified_test.ino` sketch is for component diagnostics and cannot establish integrated sorting acceptance.
3. Verify the physical tray directions using inspected test pieces before live eggs. Record the actual calibrated directions; do not infer tray identity solely from a servo angle or screen label.
4. Confirm that the camera, real ONNX model, local record storage, controller, operator identity, batch, and station preparation are ready. Simulated data must be labeled and reported separately.
5. Give evaluators the procedures and a short operating orientation. Record assistance given during a case.
6. Confirm the reference labels independently of OvaLens predictions. Unresolved labels remain unresolved; do not force them into either biological class.
7. Agree on controlled fault procedures and numeric test fixtures with the technical evaluator. Use an empty mechanism or inspected test pieces for disconnection, timing, and restart tests before using live eggs.

## 5 Requirement traceability

The following identifiers are local to this instrument. They summarize existing project requirements and objectives; they are not newly claimed implementation tasks.

| Requirement | Observable requirement | Case coverage |
| --- | --- | --- |
| R01 Access | Accounts authenticate correctly and restricted actions respect the assigned role. | AU01–AU06, AD01–AD05, IF04–IF05 |
| R02 Batch identity | Batch, operator, breed, incubation date, inventory, session, and run target remain correctly associated. | BA01–BA07, SY01–SY06, DA01–DA03 |
| R03 Readiness | Automatic movement requires inspected preparation, usable camera/model/storage, and the correct controller. | SE01–SE08, SY07, DV02, DG03 |
| R04 Capture | A sensor-held egg is captured while stationary with fresh, consistent evidence. | SO01–SO05, SO08, DG01–DG02, EV01 |
| R05 Routing | FERTILE maps to ACCEPT and the incubation tray; INFERTILE maps to REJECT and the designated Penoy stream. | SO01–SO02, SO07, SO12, EV02–EV03 |
| R06 Review | Evidence below the saved automatic threshold or invalid/synchronization evidence requires explicit review or fault recovery. | SE07, SO03–SO06, SO08–SO09, SY08 |
| R07 Run control | Pause, resume, stop, completion, and restart preserve correct egg association and prevent unauthorized motion. | SO09–SO12, SY07–SY08, DG03, UX01, EV03–EV04 |
| R08 Offline retention | Recorded scans remain available locally and synchronize later without duplicates or identity changes. | SY01–SY06, IF01–IF02, EV08 |
| R09 Records | Search, filters, images, review flags, corrections, and totals faithfully represent recorded evidence. | DA01–DA07, IF03, IF06 |
| R10 Reports | Downloads and displayed summaries agree with the selected records and distinguish estimates from observations. | DA08–DA10, EV05–EV06 |
| R11 Administration | Authorized users can manage accounts, facility settings, device records, hatch records, and snapshot downloads. | AD01–AD07, DV01–DV02, LC01–LC02, IF05 |
| R12 Evaluation | Classification, routing, tracking, timing, review frequency, and subgroup performance are measured separately. | EV01–EV08 |

The detailed source mapping and requirement conflicts are recorded in [Project Review and Test Basis](Project_Review_and_Test_Basis.md). Resolve a conflict before judging a disputed case.

## 6 Execution and verdict rules

Use the reusable case record in section 11 for every case and every specified data variant. The catalogue supplies the planned inputs, procedure, and oracle; the execution record supplies what actually happened.

| Status | Use |
| --- | --- |
| Not Executed | The procedure has not been run. This is the initial status of every case. |
| Pass | All expected outcomes for this run and variant were observed, with evidence. |
| Fail | The procedure ran and one or more expected outcomes were not met. Log a defect. |
| Blocked | The case could not be meaningfully executed because a prerequisite, agreed criterion, fixture, or equipment was unavailable. Explain the blocker. |
| Not Applicable | The case is outside the approved evaluation scope. Record the reason and the reviewer who approved exclusion. |

**Priority:** Critical = incorrect motion, routing, record loss, or unauthorized protected mutation could invalidate the evaluation; High = a major user workflow or data result; Normal = supporting behavior. Priority is not a measured defect severity.

**Techniques:** EP = representative valid/invalid inputs; BV = boundary values; DT = combinations of conditions; ST = state changes; WF = complete user workflow. **Evaluators:** U = user/operator, G = agriculture/domain validator, M = manager/client, T = technical evaluator. Several people may observe one case.

Execution sequence:

1. Freeze the test basis, numeric criteria, build, model, firmware, and calibration.
2. Run readiness and controlled component checks, then nominal sorting and run-control checks.
3. Run offline recovery, interface validation, dashboard, and administrative checks.
4. Run the quantitative trials on the approved sample without tuning the model on those results.
5. Record failures and blockers immediately. Preserve the first-run evidence.
6. After a correction, record a separate retest linked to the defect and changed build. Repeat affected neighboring cases when the change could affect them.
7. Compile a completion report and obtain signatures describing the scope actually witnessed.

An API success response, a saved scan, and a servo acknowledgement do not prove that an egg reached the correct tray. A screenshot showing a confidence score does not prove classification accuracy. Use physical observation and independently validated labels for those claims.

## 7 Functional test catalogue

### 7.1 Authentication and access

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| AU01 · R01 · High · EP · U/M/T | Valid login. Use designated active ADMIN, MANAGER, and OPERATOR accounts in separate runs. Open the dashboard, submit the correct credentials, then open the account/profile display. | Login succeeds for each account; the displayed identity and role match the test account. The appropriate permitted dashboard is accessible. |
| AU02 · R01 · High · EP · U/T | Invalid login. Separately submit an unknown email and a wrong password for a known test account. | Authentication is refused; a usable error appears; protected navigation is not granted. No password or token is included in the error display. |
| AU03 · R01 · High · EP · U/T | Incomplete login. Submit an empty email, an empty password, and both empty as separate variants. | The user is asked to provide the missing information or the request is rejected. No authenticated session is established. |
| AU04 · R01 · High · ST · U/T | Logout. Log in, log out, press Back, refresh, and try a known protected dashboard URL. | The user is returned to login and cannot resume authenticated work through browser history or refresh. |
| AU05 · R01 · High · ST · T | Expired or invalid session. Use an expired or invalid test token at the documented dashboard/API boundary and request an authenticated resource such as `/auth/me`. | Access is denied; the dashboard requests a fresh login rather than silently showing an authenticated state. Record the actual HTTP response separately. |
| AU06 · R01 · Critical · DT · U/M/T | Role restrictions. With OPERATOR and MANAGER accounts, attempt Users management by navigation and direct URL; with OPERATOR attempt facility/backup management. Repeat allowed actions with the appropriate privileged account. | Users management is ADMIN-only; facility and backup management allow ADMIN/MANAGER. OPERATOR retains permitted own-account/preferences tasks. Restricted actions do not take effect. Verify server-side restrictions separately in IF05. |

### 7.2 Batch and operator setup

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| BA01 · R02 · High · WF · U/M | Create a valid batch on the desktop. Select the registered operator; enter a unique batch, incubator, positive whole original inventory, actual set date, and one supported breed. Repeat for each breed. Save and reopen the batch. | The complete record is available with a stable identity; the operator and displayed breed match the input. The original inventory is preserved and not replaced by the current run target. |
| BA02 · R02 · High · EP · U/T | Required batch metadata. Clear the incubator or required operator selection; attempt to continue. For a field that cannot be cleared through the UI, record that restriction and test its documented interface separately. | Sorting cannot begin with incomplete required metadata; a meaningful correction is requested. No usable incomplete batch/run is created. |
| BA03 · R02 · High · BV · U/T | Desktop original inventory. Independently enter `0`, `1`, `1000000`, `1000001`, `-1`, `1.5`, and blank. Use a metadata-only test; do not physically run that many eggs. | Whole counts from 1 through 1,000,000 are accepted on the desktop; zero, negatives, fractional, blank, and excessive counts are rejected without silently changing them. |
| BA04 · R02 · High · BV · U/T | Set date. Enter a valid past date, today's date, tomorrow's date, and a malformed/impossible date as separate variants. Use an independent valid Day 10 batch for actual sorting. | Valid nonfuture dates are stored faithfully; future and invalid dates are refused by desktop setup. The saved date remains correct after reopening in UTC+08:00. Date-entry acceptance alone does not establish Day 10 eligibility. |
| BA05 · R02 · High · BV · U/T | Run quantity. For a saved inventory of 10, try targets `0`, `1`, `10`, `11`, a negative number, fractional input, and blank. | A whole target of 1 through 10 can proceed when other prerequisites are met. Invalid targets and a target greater than the original inventory are blocked; the original inventory remains 10. |
| BA06 · R02 · High · WF · U/M | Existing batch selection. Create two distinct test batches with different incubators/breeds. Search and select one on the desktop; start a short valid run, then inspect its session and scan details. | The selected batch and operator are attached to the resulting run and records. Searching/selecting does not alter unrelated batches or reassign earlier scans. |
| BA07 · R02 · High · ST · M/T | Dashboard batch lifecycle. Create a test batch through the dashboard, attempt a duplicate code, open the batch's timeline, and try a stage advance that violates its documented order. Use separate variants and restore the baseline. | Valid creation succeeds once; duplicate creation and invalid stage advancement are refused without corrupting the original. The visible stage follows the approved lifecycle. No non-Day-10 vision checkpoint is implied by administrative stages. |

### 7.3 Station and unified controller readiness

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| SE01 · R03 · Critical · ST · U/T | Safe launch. Start `edge/launcher.py` with the real unified rig connected. Observe before selecting Prepare station or Start sorting; cancel startup in a separate run. | Opening the application or cancelling startup does not begin an automatic conveyor run or record an egg classification. The operator can see the current readiness state. |
| SE02 · R03 · Critical · EP · U/T | Correct controller. Select the unified profile and confirmed controller port. Connect and inspect the reported identity. Repeat with a disconnected port, occupied port, and an unrelated controller/test sketch. | The correct production controller is identified. Missing, locked, or incompatible controllers cannot yield a falsely ready integrated station. A useful message supports correction. Record the actual firmware identity. |
| SE03 · R03 · Critical · EP · U/T | Camera unavailable. With an empty mechanism, disconnect or deny access to the selected camera, then request preparation/start. Reconnect and retry. | A missing real camera or stale preview prevents automatic sorting. Recovery requires usable fresh camera input; a simulated image is not accepted as physical-test evidence. |
| SE04 · R03 · Critical · EP · T | Model unavailable or incompatible. Use a designated test configuration with a missing ONNX model, then an incompatible class contract. Launch and request a real sorting run. | The station identifies that a verified two-class model is unavailable and refuses real sorting/recorded production classification. Unsaved preview must not be represented as a successful scan. |
| SE05 · R03 · Critical · ST · U/T | Preparation inspection. Attempt Prepare/Start before confirming an empty inspected conveyor. Then complete the inspection, valid controller connection, camera checks, and prescribed empty-station preparation. | Start remains unavailable or is rejected until preparation succeeds. Completing inspection alone does not bypass the hardware, storage, camera, model, or batch checks. |
| SE06 · R03 · Critical · ST · U/T | Calibration change. Prepare the empty station, then change camera alignment or a motion/gate calibration. Try starting without revalidation; complete the prescribed revalidation and retry. | The old prepared state is invalidated; sorting requires preparation for the changed configuration. Saved settings remain those actually selected. |
| SE07 · R06 · Critical · BV · U/T | Saved automatic threshold. Enter `0.6999`, `0.70`, `0.85`, `0.99`, `1.00`, and blank as separate variants in station automatic-sort settings. Save a valid value, restart, and reopen it. | Only 0.70–0.99 is accepted by station settings. The saved valid value persists and becomes the routing threshold T. Invalid input cannot silently lower the floor. If the UI rounds input, document its precision and execute remaining boundaries at an approved external configuration interface. |
| SE08 · R03 · High · WF · U/T | Component checks on empty rig. Using production operator tools or the documented production interface, observe lamp on/off, inspected short conveyor movement, IR indication, and gate positions. Return the mechanism to its prescribed ready condition. | Each action affects the intended component, with the corresponding visible status. The gate's physical fertile/infertile direction is documented. A diagnostic-script result alone is not counted as integrated sorting success. |

### 7.4 Capture classification and sorting control

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| SO01 · R04/R05 · Critical · WF · U/G/T | Fertile route. With all entry conditions satisfied, run a uniquely identified, independently labeled FERTILE test egg. Capture its displayed class, score, scan identity, and uninterrupted video to its destination tray. | For stable valid FERTILE evidence at or above T, a corresponding local scan is recorded and the physical egg goes to the incubation tray with ACCEPT. A disagreement with the reference label is recorded, not relabeled to match the prediction. |
| SO02 · R04/R05 · Critical · WF · U/G/T | Infertile route. Repeat SO01 with an independently labeled INFERTILE egg and record its physical destination. | For stable valid INFERTILE evidence at or above T, the matching local scan is recorded and the egg goes to the designated Penoy/reject stream with REJECT. Handling outcome and class correctness are recorded separately. |
| SO03 · R06 · Critical · BV/DT · T | Automatic threshold boundary. Use the approved external evidence fixture with confidence T−0.0001, T, and T+0.0001, independently for both classes, holding all other validity/stability conditions true. At T=0.85 also try 0.80. | Evidence below the saved T requires MANUAL_REVIEW. Evidence equal to or above T is eligible for automatic routing only when the other capture/readiness conditions pass. At T=0.85, a 0.80 result requires review. Label this fixture-based control test separately from real model accuracy. |
| SO04 · R04/R06 · Critical · DT · U/T | Unstable evidence. Present an approved external camera sequence or controllable test piece that produces conflicting classes or changes position during the held capture. Record the sequence and UI response. | Conflicting or unstable evidence cannot authorize automatic routing; the egg remains held for review or fault recovery. A frame from an earlier egg is not accepted as current evidence. |
| SO05 · R04/R06 · Critical · EP · U/T | Sensor without valid egg image. With an inspected test piece, trigger the IR hold while the camera sees an empty/obstructed chamber. Repeat with two visible eggs and a clearly invalid capture. | The system does not invent a valid single-egg automatic decision. Review or an explicit error identifies the invalid capture; no extra physical egg is released on an unverified class. Record separately whether a review resolves the event as empty. |
| SO06 · R06 · Critical · ST · U/G | Resolve a held review. Produce a review event. Wait without answering, then choose FERTILE or INFERTILE after expert inspection in separate runs; exercise the available empty/reject-event choice only when the chamber has been confirmed empty. | Waiting does not automatically release the egg. A permitted explicit decision resolves the event; the final class and manual-review provenance are retained. An empty confirmation does not create a biological egg scan. |
| SO07 · R05 · Critical · DT · U/G/T | Alternating destinations. Run an identified FERTILE, INFERTILE, FERTILE, INFERTILE sequence with feed spacing permitted by the mechanism. Record each scan/holder and actual tray. | Each egg keeps its own class and identity through transport. Gate movement for one egg does not route another egg using the previous result. Record command-following and reference-label correctness independently. |
| SO08 · R04/R06 · Critical · DT · T | No timely fresh evidence. Feed an approved external camera fixture with repeated timestamps/frames, delayed frames, or no stable sequence within the two-second capture decision window. Record the actual mode and fixture settings. | Repeated/stale evidence or failure to obtain the required stable evidence cannot authorize automatic routing. Review/error appears. The configured settling period is recorded separately from the capture decision window. If the required external fixture is unavailable, mark Blocked. |
| SO09 · R06/R07 · Critical · ST · U/T | Arrival or clearance conflict. On an empty rig or with inspected test pieces, obstruct clearance or introduce the next test piece before the prior egg has cleared the gate, using the agreed fault procedure. | Unexpected arrival/clearance synchronization cannot silently reuse an earlier decision. The conveyor holds or faults, identifies the recovery need, and requires explicit inspection before resuming. |
| SO10 · R07 · Critical · ST · U/T | Pause and resume. Request pause during a normal short run. Observe the completed safe boundary, retained pending egg, and totals; wait; then resume without changing the setup. | The application clearly distinguishes pausing/paused from stopped. It reaches a controlled paused state and resumes the same run without skipping an egg, duplicating a scan, or losing its pending route. |
| SO11 · R07 · Critical · ST · U/T | Stop during work. In separate inspected trials request Stop while indexing, during capture, and while held for review. Observe the mechanism and records, then attempt resume/start without reinspection. | Stop takes effect without a late prediction restarting motion. The run is visibly stopped/interrupted and existing records remain. Continued sorting requires the prescribed inspection/preparation rather than silently continuing the old movement. Measure response time in EV06. |
| SO12 · R05/R07 · Critical · ST · U/G/T | Target completion and drain. Set a target of three test eggs, supply exactly three, and observe until the final egg has physically cleared the gate. Inspect the final session summary and attempt an unrequested fourth feed in a separate controlled run. | The three eggs retain distinct records and routes, and normal completion occurs after the final required route/drain. An additional unexpected egg does not silently enter an already completed target. Physical completion is verified by observation, not only by a displayed count. |

### 7.5 Offline operation retention and recovery

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| SY01 · R02/R08 · Critical · ST · U/T | Start offline. With cached/approved operator details and the backend unreachable, create/select a complete local batch and perform an otherwise ready short run. Inspect local history and its export. | Network unavailability does not prevent permitted local batch/run operation. Each recorded egg remains available with stable batch, session, operator, and scan identity; synchronization is shown as pending/unavailable. |
| SY02 · R08 · Critical · ST · U/T | Lose network mid-run. Disconnect only the backend network during a normal run, leaving the host-to-ESP32 and camera connected. Finish the short run and inspect local history. | Physical control continues under local readiness conditions without waiting for an HTTP timeout on each egg. Local scans remain available; failed uploads remain pending. Controller or evidence faults are a separate condition and still require a hold. |
| SY03 · R02/R08 · High · ST · U/M/T | Reconnect. Restore the backend after SY01/SY02. Wait through the documented retry interval and inspect dashboard batch/session/scans and the local sync state. | The original batch, session, and scans appear under their original identities, with correct operator, counts, stage, and timestamps. Pending acknowledgements clear only when confirmed. Record measured recovery time; use the agreed limit rather than an invented one. |
| SY04 · R08 · Critical · ST · T | Retried or repeated upload. Interrupt a test upload acknowledgement or replay the same approved scan payload through the documented interface. Compare record IDs, totals, and export before/after. | A repeated scan ID does not create another scan or inflate counts. The initial record is retained. A successful retry does not masquerade as a second physical egg. |
| SY05 · R08 · High · ST · U/M/T | Image retry. Delay/reject only the image upload for a uniquely identified scan, while allowing the record upload. Observe the dashboard, restore image service, and revisit the same scan after retry. | The record is retained while its image is pending/unavailable. The correct captured image later appears on that scan without an additional scan or an image from another egg. |
| SY06 · R02/R08 · Critical · DT · T | Conflicting batch registration. In an isolated test environment create a backend batch with the same identity/code but conflicting metadata as an offline local batch, then reconnect. | The conflict is reported. Existing evidence is neither silently overwritten nor reassigned to another batch. The affected operation is blocked for resolution; unrelated eligible records can continue synchronizing. |
| SY07 · R03/R07 · Critical · ST · U/T | Local storage unavailable. In a disposable test configuration deny the designated local record/image output location or exhaust a bounded test volume. Try preparation and a scan; restore storage afterward. | The station refuses to claim successful durable recording or release an egg based on an unsaved decision. The operator receives a storage problem and can recover after restoring storage and preparing again. Preserve any partial record as an observation. |
| SY08 · R06/R07/R08 · Critical · ST · U/T | Controller loss and host restart. In separate inspected trials disconnect the unified USB link during motion, then restart the application after an interrupted or offline run. Verify old local records and try to start again. | Link loss brings motion to the defined held/fault condition. Restart preserves already recorded evidence and pending uploads and does not automatically resume motion. Incomplete runs require inspection/recovery; missing identities or uncertain egg positions are not guessed. Measure link-loss behavior in EV06. |

### 7.6 Dashboard records analytics and reports

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| DA01 · R02/R09 · High · WF · U/M | Live overview. Synchronize a small independently counted test run, refresh Overview, and select the relevant batch. Compare totals with the baseline and the test ledger. | Batch-specific and overall figures reflect the intended records with the documented refresh behavior. A selected batch does not display totals copied from another batch. |
| DA02 · R02/R09 · High · EP · M | Batch search and detail. Create distinguishable test batches and search by code/incubator; apply breed, stage, and status filters individually and in combination; open a matching batch. | Only matching batches appear; selected details and session history belong to that batch. Clearing filters restores the appropriate full list. |
| DA03 · R09 · High · EP · U/M | Scan search and pagination. Use a test dataset larger than one page, including distinct batch and scan IDs. Search by scan number/ID/batch, move forward/back, and clear the search. | The correct matching records and total are displayed without page duplication or unexplained omission. Changing a filter does not strand the user on an invalid empty page. |
| DA04 · R09 · High · DT · U/M/T | Class, review, confidence and date filters. Use known records on both sides of the available confidence/date boundaries and both biological classes. Apply each filter and then combined filters, using the UI's actual supported controls. | Results match the selected conditions and displayed boundary definitions. Review filtering follows the recorded action/approved rule; it is not a third class. Record actual date time-zone behavior. An unsupported control is not invented for this case. |
| DA05 · R09 · High · WF · U/G/M | Scan evidence. Open a uniquely identified scan and compare its image, displayed class, confidence, batch/session identity, and time with the recorded source capture. Repeat for an image-pending record. | The capture and its result stay paired. Missing images are identified rather than replaced by another scan. A stored confidence value is displayed consistently with its documented percent conversion and rounding. |
| DA06 · R09 · High · ST · U/G/M/T | Historical correction. Through the dashboard, correct a designated test scan to the other class and enter a reason. Reopen the scan, audit view where permitted, batch totals, and exported report. | The correction and its reason/provenance are retained, totals update consistently, and audit evidence identifies the change. Correcting history does not pretend to physically reroute an egg that already left the sorter. |
| DA07 · R09 · High · DT · M/T | Count reconciliation. Use ten stored test scans: six FERTILE and four INFERTILE, with two of these ten marked MANUAL_REVIEW. Compare session, batch, overview, and review-filter totals. | Total scans = 10; fertile = 6; infertile = 4; review = 2 as a subset. The total is not 12. Corrected/resolved records follow the approved review-count definition and remain auditable. |
| DA08 · R10 · High · WF · U/M | CSV downloads. Export a completed desktop session/batch and the corresponding backend batch CSV. Open each download as text or a spreadsheet and compare all expected scan IDs, classifications, actions, and times. | Files open with clear headers and complete records for the requested scope. Downloading a batch report is not misrepresented as exporting an arbitrary screen filter. No record is lost because it was on another history page. |
| DA09 · R10 · High · WF · M | PDF candling report. Generate the selected batch's PDF report/certificate and compare it with the batch ledger and configured facility details. | A readable PDF opens for the correct batch with consistent counts, dates and facility identity. A success label or filename alone is insufficient evidence of valid PDF content. |
| DA10 · R09/R10 · High · DT · U/M/T | Empty, unavailable and estimated information. Separately open a valid empty dataset, interrupt the backend, and open any forecast/capacity view. Also review a completed 10-scan, 120-second session where available. | A genuine zero/empty dataset is distinguishable from a failed load. Retry/recovery is usable. Forecasts and capacity are identifiable as estimates. The completed example gives 5 recorded scans/minute; missing end time or zero duration does not fabricate a measured throughput. |

### 7.7 Administrative functions

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| AD01 · R01/R11 · High · WF · M/T | Create accounts. As ADMIN create designated test OPERATOR and MANAGER accounts and verify their visible names, roles, and login ability in separate runs. | Each account is created once with the intended role. No self-service elevation to ADMIN is introduced as a requirement. |
| AD02 · R11 · High · EP · M/T | Duplicate/invalid account. As ADMIN try an existing email and missing or invalid required account fields as separate variants. | The request is refused with usable feedback; the original account remains intact and no duplicate active identity appears. |
| AD03 · R01/R11 · Critical · ST · M/T | Suspend and restore a test user. As ADMIN suspend a designated account, attempt a new login and an authenticated request with its previous token, then restore it and retry. | A suspended account cannot log in or use authenticated resources; restoration returns the intended access. Record existing-session behavior and server responses. |
| AD04 · R11 · Normal · WF · U/M | Own profile/preferences. Change the current user's display name and an available preference, save, and reload. Check an unrelated account as a control. | Supported changes persist for the intended scope; another person's profile is not changed. Record whether a preference is browser-local or account-wide. |
| AD05 · R01/R11 · High · ST · U/T | Password change. First supply an incorrect current password, then valid current/new values with matching confirmation. Log out and test the old and new passwords separately. | The incorrect-current attempt fails. A valid change persists; the new password works and the old password cannot establish a new session. |
| AD06 · R11 · High · BV · M/T | Facility settings. As MANAGER/ADMIN change an allowed facility field and a Penoy unit price in the test environment, confirm/save, and reload. Separately attempt a negative price. | Authorized valid settings persist; negative prices are refused. Dependent valuation uses the saved price and is labeled as an estimate. Do not assume this changes the separate desktop sorting threshold; verify that contract separately if claimed. Restore the baseline price. |
| AD07 · R11 · High · WF · M/T | Snapshot download. As MANAGER/ADMIN create a backup snapshot, refresh the archive list, and download it. Open the archive using an appropriate viewer and compare its declared table/record counts with the agreed baseline export. | A real nonempty readable snapshot is listed/downloaded with a plausible date and the declared contents. Failed creation/download has an error state. This establishes snapshot creation/readability only; it does not establish a complete disaster restore or image backup. |

### 7.8 Documented interface checks

These cases are executed by a technical evaluator against an isolated deployment through documented HTTP inputs and outputs. A hatchery operator is not expected to craft these requests.

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| IF01 · R08 · High · WF · T | Valid ingestion. With an authorized test station, registered test batch and one session, submit a documented valid scan payload to `/api/v1/scans/sync`. Read it through the documented scan/history interface. | The acknowledged scan is available under the original identities and correct class/action/score. Record accepted and duplicate counts in the response. |
| IF02 · R08 · Critical · ST · T | Duplicate ingestion. Submit the identical payload from IF01 again, then repeat after a client timeout/retry. Read totals and scan IDs through the interface. | The repeated ID is ignored as a duplicate; exactly one stored logical scan remains and aggregates do not increase. |
| IF03 · R09 · High · BV/EP · T | Invalid ingestion. In separate requests submit confidence `-0.0001` and `1.0001`, an invalid biological class, and a negative inference time; use the valid boundary controls `0` and `1` where the chosen review action makes the payload valid. | Invalid values produce documented client-error responses and no accepted scan. Valid boundary values are represented faithfully. API range acceptance alone does not authorize automatic sorting or prove safe routing. |
| IF04 · R01 · Critical · EP · T | Station authorization. Try scan synchronization and image upload with a missing API key, an incorrect key, and the authorized key as separate variants. | Missing/incorrect station credentials cannot create scans or upload their images. An authorized valid request can proceed. Record actual status/body without publishing credentials. |
| IF05 · R01/R11 · Critical · DT · T | Server role enforcement. Attempt user creation as OPERATOR/MANAGER and facility mutation or backup creation as OPERATOR, using direct documented API requests. Repeat authorized variants. | Server-side permission checks refuse disallowed mutations even if a dashboard control is bypassed. Authorized requests behave according to the role contract. Test read-access policy separately if the client requires private analytics/history. |
| IF06 · R09 · High · EP · T | Missing entities and no-match search. Request a syntactically valid nonexistent scan/batch ID, then a valid search with zero matches as separate variants. | A missing entity returns a clear not-found response; a successful empty search returns a valid empty result. Neither produces invented records, a generic success with unrelated data, or an unexplained server exception. |

### 7.9 Device monitoring diagnostics and follow up

| ID and assignment | Scenario and procedure | Expected result |
| --- | --- | --- |
| DV01 · R11 · High · ST · M/T | Device heartbeat. Run a registered real test station and open Devices. Match its identity, model/platform information and last-seen time. Stop only its heartbeat/network, wait through the documented stale interval, then reconnect. | Current/stale/offline indicators follow the approved heartbeat and refresh policy. Another station's status is not substituted. Backend reachability status is not presented as proof that every physical component is ready. Agree the stale interval before a timed verdict. |
| DV02 · R03/R11 · High · ST · M/T | Device calibration metadata. With an authorized account save a designated device's calibration record, refresh and reopen it. Observe the empty physical station throughout. | The permitted metadata persists on the selected device. Saving a dashboard calibration record does not itself start motion or replace local inspected preparation. An unauthorized account cannot perform the protected mutation; test directly at the API as an IF05 variant. |
| DG01 · R04 · High · WF · U/G/T | Manual diagnostic scan. Outside an automatic run, select the prescribed diagnostic workflow and scan an inspected stationary Day 10 egg. Observe its class, confidence and saved-versus-preview status. | A valid real diagnostic capture is paired with its displayed result and correct identity when saved. Preview-only or simulation output is identifiable and cannot be mistaken for a successful physical production scan. |
| DG02 · R04/R06 · Critical · BV/DT · U/T | Diagnostic review rule. Use an approved external fixture at 0.7499, 0.7500 and 0.7501 for each class, then test an invalid/no-egg capture. Hold detection filtering and other validity conditions suitable for the test. | Valid diagnostic evidence below 0.75 requires review; at/above 0.75 follows the diagnostic rule. Changing automatic T does not silently redefine this diagnostic boundary. An invalid capture cannot produce a successful verified biological scan. Mark exact-score runs Blocked if no suitable external fixture exists. |
| DG03 · R03/R07 · Critical · ST · U/T | Manual lamp and shutdown. On an empty rig, activate the manual lamp through the operator controls, release/turn it off, then separately close the view, request Stop, and disconnect the controller using the agreed procedure. Record any keepalive and timeout configuration. | The lamp follows the intended control, releases on the prescribed exit/stop path, and does not remain on indefinitely after lost control. Observe actual switch-off timing against the approved timeout. A subsequent automatic run cannot begin with an unacknowledged manual-lamp state. |
| LC01 · R11 · High · BV/ST · M/T | Actual hatch follow-up. On a disposable eligible batch, record a valid hatch completion; in separate baseline-restored variants try negative counts and totals inconsistent with the eligible batch. Inspect batch status, actual hatch metrics and forecast labels. | Valid follow-up is retained and the prescribed completion state appears. Invalid/inconsistent counts are refused according to the approved hatch-accounting rule. Actual hatch records remain distinct from estimates; this administrative test makes no claim of later-day vision classification. Resolve the inventory rule before judging a disputed count. |
| LC02 · R11 · High · ST · M/T | Batch removal/archive. On disposable test records, open the remove/archive action and cancel. Then confirm the permitted action on an approved disposable record; exercise a linked-history record only under the agreed retention policy. | Cancel preserves the record. Confirmation has the documented delete/archive effect on the intended batch, and linked history follows the approved retention policy. No unrelated batch or evaluation evidence is removed. |
| UX01 · R01/R07 · High · WF · U/M/T | Usable critical controls. On the actual station display and agreed browser sizes, navigate by the supported input methods, open/close dialogs, and reach review, pause, Stop, login, filters and reports. Record display sizes and assistance. | Required actions and error/review states remain visible and usable without clipped critical controls. Keyboard focus and dialog exit are understandable where supported; class/review meaning is conveyed by text as well as color. Record workflow observations separately from any optional usability questionnaire. |

## 8 Decision and boundary coverage

### 8.1 Automatic routing decision table

Use SO01–SO09 to cover these rules. Every automatic rule assumes all station and batch prerequisites have passed.

| Rule | Evidence/condition | Required observable response |
| --- | --- | --- |
| D1 | Valid stationary single egg; consistent FERTILE evidence; confidence at least saved T | Record the matching result and route ACCEPT to the incubation tray. |
| D2 | Valid stationary single egg; consistent INFERTILE evidence; confidence at least saved T | Record the matching result and route REJECT to the designated Penoy stream. |
| D3 | Either class below saved T | Hold for MANUAL_REVIEW; no automatic route. |
| D4 | Conflict, stale/repeated frames, or no stable result within the capture window | Hold for review or the specified fault recovery; do not reuse an earlier egg's result. |
| D5 | IR egg event but no valid single-egg capture | Explicit review/error; no invented automatic scan decision. |
| D6 | Egg/holder position, arrival, gate clearance, or controller acknowledgement is inconsistent | Hold/fault and require explicit inspection/recovery. |
| D7 | Backend network unavailable, but local control/capture/storage remain healthy | Continue permitted local recording/control and queue uploads. Network outage alone is not a physical synchronization fault. |
| D8 | Local durable recording unavailable | No successful saved-scan claim or release based on an unsaved result. |
| D9 | Operator stops, controller link fails, or application restarts | Stop/hold according to the fault contract; no automatic restart of motion. |

### 8.2 Boundary data and reproducibility

| Boundary | Values or conditions | Execution note |
| --- | --- | --- |
| Automatic T at default | 0.6999, 0.7000, 0.7001 | All other validity and stability conditions must be held true. |
| Saved higher T | T=0.85 with 0.8499, 0.8500, 0.8501, plus 0.80 | Confirms use of the saved threshold rather than only the minimum. |
| Automatic T configuration | 0.6999, 0.70, 0.99, 1.00 | Accepted station range is 0.70–0.99. |
| Manual diagnostic review | 0.7499, 0.7500, 0.7501 | Review below 0.75; eligibility at/above 0.75 still requires valid capture. Do not apply the automatic T as this rule's oracle. |
| Stable automatic evidence | Fewer than three fresh agreeing frames; three agreeing frames spanning less than 300 ms; three spanning at least 300 ms; no valid sequence within two seconds | Run with an approved external fixture. These are capture-window values, not total mechanical cycle deadlines. |
| Unified optical timing | 39/40/41 ms detection LOW; 349/350/351 ms clearance HIGH; 599/600/601 ms lockout | Optional detailed SO09 subruns need a calibrated external stimulus and timing record. Record scheduler/sensor tolerance; do not claim 1 ms precision from a hand wave. |
| Desktop original inventory | 0, 1, 1000000, 1000001, negative, fractional, blank | Test metadata only. |
| Run target for inventory 10 | 0, 1, 10, 11, fractional, blank | No more than the saved inventory. |
| API confidence representation | Below 0, exactly 0, exactly 1, above 1 | Isolated payload test; separate schema range validation from routing eligibility. |

**Fixture limitation:** Egg confidence is a model output and cannot be set reliably by choosing a physical egg. Record exact score-boundary tests as Blocked until an approved external replay/evidence interface is available. Internal monkeypatches may support engineering tests, but do not count as independent physical black-box evidence. Preserve both the true supplied value and the rounded screen value. At displayed equality, avoid guessing the unrounded value.

## 9 Quantitative evaluation procedures

These eight procedures complement functional testing and remain **Not Executed** until real observations are supplied. A successful nominal case does not establish population accuracy. Decide the sample plan, independent egg IDs, batch/breed representation, number of repeat trials, and criteria before collecting final evidence. No universal participant or egg sample size is asserted here.

### EV01 Egg classification against independent reference labels

**Covers R04/R12; U/G/T.** The domain validator establishes a written Day 10 candling guide and labels held-out eggs before seeing OvaLens predictions. Use the approved resolution procedure for disagreements; record unresolved eggs separately. Keep final evaluation eggs and their repeated images out of model training/tuning. Preserve the project's 70/15/15 dataset split and partition physical eggs together to avoid treating images of the same egg as independent held-out eggs.

For each unique egg, record the initial automatic prediction, unrounded confidence, saved T, review referral, reference label, and later human resolution separately. Do not replace the original prediction with a correction when computing model accuracy.

Use FERTILE as the positive class: TP = reference fertile/predicted fertile; FN = reference fertile/predicted infertile; FP = reference infertile/predicted fertile; TN = reference infertile/predicted infertile.

Report the two-class confusion matrix for eggs with a valid original binary prediction, plus counts of no prediction, unresolved reference label, and review referral. Predictions below T can still be compared diagnostically when a binary prediction exists, but must be identified as referred. Also report automatic-decision coverage and automatic-only accuracy so review referrals cannot silently improve reported model performance. Include raw denominators and confidence intervals where the analysis plan provides them.

### EV02 Physical routing and destination accuracy

**Covers R05/R12; U/G/T.** Video the uniquely identified egg from capture/holder to the actual tray. Record the predicted route, commanded route, manual decision if any, and actual tray. Count wrong tray, unreleased, dropped, jammed, and unconfirmed outcomes separately.

Report both **command-following accuracy** (correct observed tray relative to the authorized route / eggs given a route) and **end-to-end destination accuracy** (correct observed biological destination relative to expert reference / all eligible labeled trial eggs). Report automatic and manually assisted outcomes separately. A correct servo response to a wrong prediction is a mechanism success and a biological destination error. Unconfirmed/dropped/jammed outcomes do not disappear from the end-to-end denominator.

### EV03 Egg and cradle association

**Covers R05/R07/R12; U/G/T.** Use an externally tracked sequence of unique egg/cradle labels, including alternating classes, allowed gaps/spacing, and pause/resume trials. Compare the physical sequence with scan/holder identity and observed tray. Avoid marks that alter the transmitted-light region.

Record correctly associated eggs / all externally tracked eggs, duplicate identities, skipped identities, swapped results, and events that cannot be confirmed. Screen sequence numbers alone do not prove physical identity continuity.

### EV04 Successful cycles and manual review frequency

**Covers R07/R12; U/G/T.** Define an attempted cycle before the trial, for example from a confirmed egg arrival to its observed completed route. Run the approved cohort under recorded settings without omitting faulted attempts. Record completion, review referral, operator resolution, stop/fault, and damage/jam observations.

Report unassisted successful cycles / all attempted cycles, assisted completions separately, review referrals / all attempted egg cycles, and failures with causes. Preserve referral-event history because a dashboard's current review count may fall after a historical correction. Record assisted interventions rather than silently counting them as automatic success.

### EV05 End to end processing time and throughput

**Covers R10/R12; U/T.** Timestamp physical arrival, stationary capture start/end, decision availability, release, and final observed tray arrival. Use video or synchronized external observation. Measure the approved full run from Start to final physical drain completion, including pauses/review unless a separately named active-only metric is required.

Report median, 95th percentile, minimum, maximum, number of observations, and timing method for full-cycle seconds. Report physically completed eggs / elapsed run minutes. Separately report the application's stored scans/minute, including its persisted start/end timestamps. Explain differences between scan completion and physical completion. A 10-scan, 120-second session gives 5 scans/minute; it does not automatically prove five correctly sorted physical eggs/minute.

### EV06 Prediction readiness and stop or link loss response

**Covers R10/R12; T.** On the actual target host, record externally observed capture-to-result availability. If the system exposes `inference_ms`, report that as an instrumented model metric rather than claiming that video independently measures inference alone. Record warmup state, model, image size, host, and repeat count.

Use the current Chapter 1 target of **model inference no more than 200 ms/image on the selected Raspberry Pi** as the provisional requirement basis, pending resolution of the repository's conflicting latency guidance. Specify whether acceptance applies per sample, to a percentile, or another statistic before testing. Also verify that the usable decision arrives during the stopped candling interval before routing is required.

In separate inspected trials, measure Stop request to cessation of motion and USB/heartbeat loss to cessation of motion. The unified firmware currently declares a 3000 ms link timeout; host-detected faults may stop earlier. Agree the permitted measurement tolerance and final acceptance limit before the run. Do not infer physical stopping time only from the configured watchdog value.

### EV07 Performance by breed and batch

**Covers R12; G/T.** Apply EV01–EV05 to the approved IP-Itim, IP-Khaki, and IP-Kayumanggi Day 10 cohorts and report results by breed and incubation batch. Record actual natural class counts; do not claim balanced representation when it was not sampled.

For each subgroup report unique eggs, fertile/infertile reference counts, unresolved labels, confusion counts, missing predictions, review referrals, automatic coverage, sorting outcomes, and timing denominators. If a class or subgroup has too few observations, state the limitation and leave undefined metrics undefined. Do not invent subgroup evidence from pooled results.

### EV08 Offline recovery consistency

**Covers R08/R12; U/M/T.** Run an identified cohort during a controlled backend outage, export the local evidence, restore the network, and compare the subsequently visible central records by scan identity and associated image. Record outage length and time from restoration to final acknowledgement.

Report unique local scans retained, unique central scans recovered, missing IDs, duplicate IDs, mismatched metadata/images, and recovery duration. The proposed integrity criterion is zero lost, duplicated, or incorrectly associated acknowledged test scans. Agreement of total counts without agreement of identities is insufficient.

## 10 Criteria to approve before formal testing

The following are proposed project criteria. They require review before they become formal acceptance rules. The draft does not replace missing requirements with arbitrary percentages.

| Item | Proposed rule or field | Approved by and date |
| --- | --- | --- |
| Functional completion | Every applicable required case and required data variant has a supported verdict; no unexecuted case is called passed. | __________ |
| Critical failures | No unresolved Critical functional failure; no unresolved defect causing unsafe/unrequested motion, wrong egg association, lost acknowledged records, or unauthorized protected mutation. | __________ |
| Other required workflows | All applicable mandatory cases pass; any exclusion or conditional acceptance has written scope and rationale. | __________ |
| Automatic confidence | Saved station T is within 0.70–0.99; below T requires review. The test campaign records its actual saved value. | __________ |
| Manual diagnostic confidence | Below 0.75 requires review; exercise this boundary as a separate diagnostic subrun if diagnostics are within the final accepted scope. | __________ |
| Classification | Overall accuracy at least ____; fertile recall at least ____; infertile recall at least ____; sample plan ____; handling of no predictions/referrals ____. | __________ |
| Routing and tracking | Required destination accuracy ____; command-following accuracy ____; association accuracy ____; treatment of failed/unconfirmed routes ____. | __________ |
| Cycle performance | Required unassisted cycle success ____; maximum review frequency ____; minimum physically completed eggs/min ____; timing statistic/limit ____. | __________ |
| Inference | Provisional Chapter 1 target: no more than 200 ms/image on selected Raspberry Pi; approved statistic and final threshold after conflict resolution: ____. | __________ |
| Stop and link loss | Physical stopping limit ____; timing method and tolerance ____; tested controller/host versions ____. | __________ |
| Offline consistency | Zero lost/duplicated/misassociated test scan IDs; recovery time limit ____ for an outage lasting ____. | __________ |
| Participant and egg sample plan | Evaluator roles/count ____; unique eggs and batches ____; breed/class distribution ____; repeats ____; adviser/client approval ____. | __________ |

Do not lower a threshold after seeing a failing result. If the agreed requirement changes, preserve the previous result and record the new requirement version and reason.

## 11 Reusable execution forms

### Form A Individual case execution record

Duplicate this form for each case, each data variant, and each retest.

| Field | Entry |
| --- | --- |
| Campaign / run / case ID / variant | __________ |
| Requirement and catalogue version | __________ |
| Module and scenario | __________ |
| Priority and technique | __________ |
| Evaluator / role / witness | __________ |
| Date and time with time zone | __________ |
| Build / firmware / model / settings identifier | __________ |
| Preconditions and baseline records | __________ |
| Exact input data / egg IDs / fixture | __________ |
| Steps actually performed | 1. __________  2. __________  3. __________ |
| Expected result / approved criterion | __________ |
| Actual result | __________ |
| Status | Not Executed / Pass / Fail / Blocked / Not Applicable |
| Evidence filenames / video timestamps / scan IDs | __________ |
| Assistance or deviations | __________ |
| Defect or blocker ID | __________ |
| Retest link and changed configuration | __________ |
| Evaluator initials and date | __________ |

Example of a useful actual result: “At 10:14:22 UTC+08:00, egg E017 displayed INFERTILE at 0.9123, scan ID recorded in evidence EV-SO02-01, and entered the designated reject tray at video 00:18.4.” This is an illustration of recording style, **not an OvaLens result**. Replace it with an actual observation.

### Form B Execution register

Use one row for each case variant or retest. Initially enter Not Executed. Do not use a checkmark that cannot distinguish failure, blocking, and nonexecution.

| Case ID and variant | Run ID | Actual result summary | Status | Evidence | Defect / retest | Evaluator / date |
| --- | --- | --- | --- | --- | --- | --- |
| __________ | __________ | __________ | Not Executed | __________ | __________ | __________ |
| __________ | __________ | __________ | Not Executed | __________ | __________ | __________ |
| __________ | __________ | __________ | Not Executed | __________ | __________ | __________ |

### Form C Egg reference and physical outcome ledger

One row represents one uniquely identified physical egg in one trial. Additional views of that egg retain the same egg ID and a distinct capture/repeat identifier.

| Trial / egg ID | Breed / batch / verified day | Reference label / validator | Initial prediction / score / T | Review event / human decision | Scan / holder identity | Authorized route / actual tray | Times / evidence / issue |
| --- | --- | --- | --- | --- | --- | --- | --- |
| __________ | __________ | __________ | __________ | __________ | __________ | __________ | __________ |
| __________ | __________ | __________ | __________ | __________ | __________ | __________ | __________ |

Reference-label resolution: first validator __________; second validator or agreed adjudication __________; disagreement __________; final label or unresolved __________; date __________. Keep original label observations, not just the adjudicated label.

### Form D Quantitative summary

| Metric | Numerator | Denominator and exclusions | Value / uncertainty | Criterion | Verdict / evidence |
| --- | --- | --- | --- | --- | --- |
| Binary prediction accuracy | TP + TN | Eggs with resolved reference and valid original binary prediction | __________ | __________ | __________ |
| Fertile recall | TP | TP + FN | __________ | __________ | __________ |
| Infertile recall | TN | TN + FP | __________ | __________ | __________ |
| Fertile precision | TP | TP + FP | __________ | __________ | __________ |
| Fertile F1 | 2 × TP | 2 × TP + FP + FN | __________ | __________ | __________ |
| No valid prediction | No-prediction eggs | All eligible reference-labeled evaluation eggs | __________ | __________ | __________ |
| Automatic-decision coverage | Eggs with valid unassisted automatic decisions | All attempted eligible egg cycles | __________ | __________ | __________ |
| Automatic-only accuracy | Correct unassisted binary decisions | All unassisted binary decisions with resolved reference | __________ | __________ | __________ |
| End-to-end destination accuracy | Eggs observed in the biologically correct tray | All eligible reference-labeled trial eggs, including unconfirmed routing failures | __________ | __________ | __________ |
| Command-following accuracy | Observed tray agrees with authorized route | All eggs given an authorized route, including unconfirmed routing failures | __________ | __________ | __________ |
| Cradle association accuracy | Correct confirmed egg-to-record associations | All externally tracked eggs | __________ | __________ | __________ |
| Unassisted successful cycles | Completed correct cycles without intervention | All attempted cycles under the approved definition | __________ | __________ | __________ |
| Review referral rate | Attempted egg cycles referred to a human | All attempted egg cycles | __________ | __________ | __________ |
| Physical throughput | Physically completed eggs | Full elapsed run minutes, with pause policy stated | __________ | __________ | __________ |
| Offline identity consistency | Recovered matching unique scan IDs | Unique locally recorded IDs expected to sync | __________ | __________ | __________ |

For every percentage, multiply the fraction by 100. A zero denominator is **Undefined**, not 0% or 100%. List unresolved reference eggs, missing predictions, missing physical outcomes, manual interventions, and exclusions alongside the metrics. Copy the summary for each breed and batch; use the same definitions. Object-detection mAP and training curves require a separate annotated-detection evaluation and are not established by these functional checks.

Timing summary: method __________; host/configuration __________; sample count __________; median __________; p95 __________; minimum/maximum __________; units __________; inference-only versus capture-to-result versus full mechanical cycle __________.

### Form E Defect and retest record

| Field | Entry |
| --- | --- |
| Defect ID / linked case and run | __________ |
| Observed failure and evidence | __________ |
| Expected result | __________ |
| Steps and data to reproduce | __________ |
| Severity and operational effect | __________ |
| Assigned person and correction/build | __________ |
| Retest run / date / evaluator | __________ |
| Retest actual result / evidence / status | __________ |
| Neighboring cases repeated | __________ |
| Closure or accepted limitation and approver | __________ |

Retain the original failure; a successful retest does not erase it.

### Form F Campaign completion report

| Item | Record |
| --- | --- |
| Campaign / configuration / evaluation dates | __________ |
| Approved scope and exclusions | __________ |
| Applicable planned case variants | __________ |
| Pass / Fail / Blocked / Not Executed | ____ / ____ / ____ / ____ |
| Approved Not Applicable variants | __________ |
| Executed functional pass rate | Pass / (Pass + Fail) × 100 = ____; do not include Blocked or Not Executed as passes |
| Functional execution completion | (Pass + Fail) / all applicable planned variants × 100 = ____ |
| Critical case outcomes and open defects | __________ |
| Quantitative criteria and results | __________ |
| Deviations, assistance, limits and missing evidence | __________ |
| Defect corrections and retests | __________ |
| Final recommendation | Accepted for stated scope / Conditionally accepted / Not accepted / Evaluation incomplete |
| Conditions and scope of recommendation | __________ |

Do not describe the entire system as accepted merely because the executed subset has a high pass rate. Report model, mechanism, data integrity, user workflow, and outstanding criteria separately.

### Form G Evaluation acknowledgement and sign off

“I confirm that I performed or witnessed the activities identified below and that the recorded observations reflect those activities. My signature applies to the listed scope and recorded conditions.”

| Capacity | Name / affiliation / relevant experience | Cases or evidence reviewed | Recommendation and conditions | Signature / date |
| --- | --- | --- | --- | --- |
| User evaluator | __________ | __________ | __________ | __________ |
| Agriculture or hatchery domain validator | __________ | __________ | __________ | __________ |
| Manager or client representative | __________ | __________ | __________ | __________ |
| Technical evaluator | __________ | __________ | __________ | __________ |
| Researcher preparing the record | __________ | __________ | __________ | __________ |
| Adviser or academic reviewer if required | __________ | __________ | __________ | __________ |

Witnessing a component demonstration does not establish full-system acceptance. Domain validation, functional observation, and academic approval have distinct scopes even when a person occupies multiple roles.

## 12 Suggested manuscript wording

### Before execution

“Black-box testing will evaluate OvaLens by comparing specified outcomes with observable behavior under valid, invalid, boundary, and interrupted operating conditions. The test plan covers the desktop station, unified controller, Day 10 candling and sorting workflow, offline record retention and synchronization, and administrative dashboard. Each case will record its prerequisites, inputs, procedure, expected and actual results, execution status, and evidence. Intended hatchery users will evaluate operational tasks, while an agriculture or hatchery specialist will validate the reference candling labels and observe physical outcomes. Quantitative classification and sorting trials will be reported separately from functional pass/fail results.”

### After execution

“Testing was conducted on [dates] at [location] using [identified build, model, firmware, host, and settings]. Of [number] applicable planned functional case variants, [number] passed, [number] failed, [number] were blocked, and [number] remained unexecuted. [Participants and roles] performed or witnessed the identified procedures. The functional pass rate among executed variants was [value], with [value] execution completion. Separate trials involving [number] unique Day 10 eggs produced [measured results with stated denominators]. [Open defects, retests, deviations, and limitations] qualify these findings.”

Replace every bracketed field with verified records. Do not copy the sample narrative into the results chapter with invented figures or imply formal testing has already occurred.

## 13 References

1. Supplied CacaoDx black-box testing reference. [Google document](https://docs.google.com/document/d/1cxyTO3B0cykP_3A2Uzg-WYT5wjpAgy82hYFwn63_BOM/edit). Used for form structure only; its outcomes and features do not transfer to OvaLens.
2. International Software Testing Qualifications Board. (2024). [Certified Tester Foundation Level syllabus, version 4.0.1](https://istqb.org/wp-content/uploads/2024/11/ISTQB_CTFL_Syllabus_v4.0.1.pdf). Sections 2.2.1, 4.2, 5.3 and 5.5 inform technique selection and reporting.
3. International Software Testing Qualifications Board. (2019). [Certified Tester Acceptance Testing syllabus, version 1.0](https://istqb.org/wp-content/uploads/2024/11/ISTQB-CT-AcT_Syllabus_v1.0_2019.pdf). Requirements, measurable acceptance criteria, and stakeholder collaboration.
4. Agile Alliance. [Acceptance testing](https://agilealliance.org/glossary/acceptance-testing/). Supports involving users/domain experts when discussing acceptance behavior.
5. Northern Arizona University US Software capstone team. (1998). [GNAT detailed test plan](https://sce.nau.edu/capstone/projects/CSE/1997/ussoftware/docs/testplan.html). Historical capstone example of explicit test data and black-box boundary/equivalence analysis; not an institutional rule for OvaLens.
6. OvaLens project test basis. `AGENTS.md`, `PROJECT_PLAN.md`, current manuscript Chapter 1, and the implemented surfaces mapped in [Project Review and Test Basis](Project_Review_and_Test_Basis.md). Repository review date: 30 October 2026.
