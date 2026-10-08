"""Plain operator instructions, independent of Tk and firmware terminology."""


def cycle_cue(status):
    state = status["state"]
    reason = status.get("reason", "")
    if state == "SEARCHING":
        return "Feed next egg", "Place one egg on the conveyor.", "ready"
    if state in {"LIGHTING", "STABILIZING", "CLASSIFYING", "SAVING"}:
        return "Inspecting egg", "Wait while the egg is held under the camera.", "wait"
    if state == "ROUTING":
        return "Positioning gate", "Wait. The conveyor stays stopped during the servo stroke.", "wait"
    if state == "DISPLAYING":
        return "Egg classified", "The gate is ready. Wait for the egg to pass.", "wait"
    if state == "INDEXING":
        return "Wait — egg passing", "Feed the next egg when this message changes.", "wait"
    if state == "MANUAL_REVIEW":
        return "Inspect this egg", reason or "Choose a review decision below.", "review"
    if state == "RECOVERY_REQUIRED":
        return "Sorting stopped", reason or "Inspect the conveyor before starting again.", "error"
    if state == "COMPLETE":
        return "Batch complete", "Saving final totals locally.", "ready"
    return "Wait", "The station is preparing for sorting.", "wait"
