# OvaLens Black Box Testing Draft

Foundation University | College of Computer Studies

This form checks whether OvaLens produces the expected results from user inputs and actions, without examining its internal code. It covers the desktop sorting station with the unified ESP32 and the web dashboard. Egg tests use Day 10 Itik Pinas samples.

Test date: ____________________    Location: ____________________

Tester name and role: ____________________    App/build tested: ____________________

Before testing: Use test accounts, test batches and agriculture-validated Day 10 eggs. For sorting, connect the unified ESP32 and camera, load the model and prepare a batch of at least three eggs. Start checks while idle unless instructed otherwise.

Instructions: Perform each listed check and record the inputs and actual outcome in Actual result / Remarks. Enter Pass when all expected results are met, Fail when any check fails, or Not tested when the check was not performed. State the reason for unperformed checks. Record each input separately when a test lists alternatives.

## Desktop station

| Test ID | Module / function | Test steps | Expected result | Result | Actual result / Remarks |
| --- | --- | --- | --- | --- | --- |
| E01 | Camera preview | 1. Open the desktop app.<br>2. Check the camera view. | A live camera image appears and no sorting starts automatically. | Not tested |  |
| E02 | Create a batch | 1. Open Batch setup.<br>2. Select the operator and a supported breed; enter a test incubator, an egg count of 1 and a valid set date.<br>3. Save and reopen the batch. | The batch is saved with the entered details, including the minimum valid egg count of 1. | Not tested |  |
| E03 | Invalid batch details | 1. Try each input separately: a blank required field, an egg count of 0, and an egg count of -1.<br>2. Try to save or continue after each input. | The app asks for valid details and does not start sorting. | Not tested |  |
| E04 | Prepare the station | 1. Connect the unified ESP32.<br>2. Inspect the empty conveyor.<br>3. Complete Prepare station. | The station shows it is ready after the required checks. | Not tested |  |
| E05 | Missing equipment | 1. With an empty conveyor, disconnect the camera or ESP32.<br>2. Try to start sorting. | Sorting is blocked and the app identifies the missing equipment. | Not tested |  |
| E06 | Fertile egg sorting | 1. Use a clear Day 10 egg labeled fertile by the agriculture evaluator.<br>2. Run the egg and observe its result and tray. | FERTILE is displayed at or above the saved sorting threshold, and the same egg reaches the incubation tray. | Not tested |  |
| E07 | Infertile egg sorting | 1. Use a clear Day 10 egg labeled infertile by the agriculture evaluator.<br>2. Run the egg and observe its result and tray. | INFERTILE is displayed at or above the saved sorting threshold, and the same egg reaches the designated reject/Penoy tray. | Not tested |  |
| E08 | Uncertain result | 1. Use a sample that produces a score below the saved automatic sorting threshold; record the sample ID, score and threshold.<br>2. Observe the conveyor and alert. | The egg is held for manual review instead of being automatically sorted. | Not tested |  |
| E09 | Manual review decision | 1. While an egg is held for review, have the evaluator inspect it.<br>2. Select the appropriate available decision. | The app records the decision and continues with the chosen route when it is safe. | Not tested |  |
| E10 | Pause and resume | 1. Start a short run.<br>2. Press Pause and wait for the paused state.<br>3. Press Resume. | The run pauses safely and resumes without losing or duplicating an egg record. | Not tested |  |
| E11 | Stop sorting | 1. Start a short run with an inspected test piece.<br>2. Press Stop.<br>3. Observe the conveyor. | The conveyor stops and stays stopped until the operator completes the required restart preparation. | Not tested |  |
| E12 | Finish a run | 1. Set a target of three eggs.<br>2. Run exactly three eggs.<br>3. Wait for the last egg to clear the sorter. | The run finishes with three records and the final egg completes its route. | Not tested |  |
| E13 | Offline operation and reconnection | 1. Disconnect the backend network while leaving the camera and ESP32 connected.<br>2. Run three eggs and note their scan IDs in local history.<br>3. Restore the network and find the same scans on the dashboard. | Scanning continues locally. After reconnection, all three scan IDs appear once on the dashboard with their original results. | Not tested |  |
| E14 | Local scan history | 1. Complete a scan.<br>2. Open the desktop scan history.<br>3. Find the recorded egg. | The matching result, batch and scan details are displayed. | Not tested |  |
| E15 | Desktop CSV report | 1. Open a completed session or batch.<br>2. Export its CSV.<br>3. Open the downloaded file. | The file opens and contains the correct records for the selected session or batch. | Not tested |  |
| E16 | Saved station settings | 1. While idle, note the current automatic sorting threshold.<br>2. Save 0.85 and reopen the setting.<br>3. Try to save 0.69.<br>4. Restore the original valid value. | 0.85 is saved and retained; 0.69 is rejected because the minimum is 0.70. The original valid setting can be restored. Preparation is required again before sorting. | Not tested |  |

## Web dashboard

| Test ID | Module / function | Test steps | Expected result | Result | Actual result / Remarks |
| --- | --- | --- | --- | --- | --- |
| W01 | Valid login | 1. Open the web dashboard.<br>2. Enter valid test-account credentials.<br>3. Log in. | The correct user account can access the dashboard. | Not tested |  |
| W02 | Invalid login | 1. Separately try an incorrect password, a blank email, and a blank password.<br>2. Try to log in after each input. | Access is refused and a useful message appears. | Not tested |  |
| W03 | Logout | 1. Log in and then log out.<br>2. Press Back or reopen a protected dashboard page. | The user must log in again before accessing protected pages. | Not tested |  |
| W04 | Create a dashboard batch | 1. Open Batches using an authorized account.<br>2. Enter valid batch details.<br>3. Save and reopen the batch. | The new batch appears with the correct details. | Not tested |  |
| W05 | Find a batch | 1. Open Batches.<br>2. Search for a known batch or apply a breed/status filter.<br>3. Clear the search/filter. | Matching batches appear; clearing the filter restores the list. | Not tested |  |
| W06 | Find and inspect a scan | 1. Open Scan Explorer.<br>2. Search/filter for a known scan.<br>3. Open its details. | The correct scan and its available image, class, confidence and batch details are displayed. | Not tested |  |
| W07 | Dashboard totals | 1. Open a test batch and independently count its stored fertile and infertile scans.<br>2. Note the batch ID and counts, then compare them with the displayed summary. | The displayed total equals the fertile plus infertile scan counts. Any manual-review count is shown separately. | Not tested |  |
| W08 | Correct a stored result | 1. Open a designated test scan using an authorized account.<br>2. Change its classification and enter a reason.<br>3. Save and reopen it. | The correction and reason are retained, and the totals update. | Not tested |  |
| W09 | Download reports | 1. Select a known batch.<br>2. Download its available CSV and PDF reports.<br>3. Open both files. | Both files open and show the selected batch's correct information. | Not tested |  |
| W10 | Device monitoring | 1. Connect the registered test station.<br>2. Open Devices and refresh its status. | The correct station identity and current connection/last-seen information appear. | Not tested |  |
| W11 | Restricted functions | 1. Log in as an operator.<br>2. Try to open Users management and facility/backup management. | The operator cannot perform actions reserved for administrators or managers. | Not tested |  |
| W12 | Manage user accounts | 1. As administrator, create a designated test operator account.<br>2. Check its role and login.<br>3. Suspend it and try a new login. | The account has the assigned role. A suspended account cannot log in. | Not tested |  |
| W13 | Facility settings | 1. As manager/administrator, change an allowed facility setting.<br>2. Save and reload. | The valid change is saved and displayed correctly. | Not tested |  |
| W14 | Backup download | 1. As manager/administrator, create a backup snapshot.<br>2. Find it in the backup list.<br>3. Download it. | The snapshot is listed and downloads successfully. | Not tested |  |

Test summary (30 scenarios): Passed ____    Failed ____    Not tested ____

## Evaluator acknowledgement

Tested by: ____________________    Role: ____________________    Signature/date: ____________________

Agriculture or hatchery evaluator: ____________________    Signature/date: ____________________

Reviewed by: ____________________    Role: ____________________    Signature/date: ____________________
