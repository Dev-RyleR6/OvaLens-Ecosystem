"""OvaLens desktop launcher: explicit preview, no unvalidated hardware motion."""
import os
import sys
from contextlib import ExitStack
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from src.ui.startup_config import show_startup_config
from src.core.camera import CameraGrabber
from src.core.inference import InferenceEngine
from src.core.inference_worker import InferenceWorker
from src.core.chamber_controller import ChamberController
from src.iot.serial_driver import ESP32SerialDriver
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp


def _stop_resource(resource):
    try:
        resource.stop()
    except Exception as exc:
        print(f"[SHUTDOWN WARNING] {type(resource).__name__}: {exc}")


def main():
    print("=" * 65)
    print("   OVALENS EDGE OPERATOR SYSTEM — FOUNDATION UNIVERSITY")
    print("=" * 65)
    device_id = os.getenv("DEVICE_ID", "STATION-01-RP5")
    config = show_startup_config(device_id=device_id)
    if config is None:
        print("[EXIT] Startup cancelled.")
        return
    try:
        camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    except ValueError as exc:
        raise ValueError("CAMERA_INDEX must be an integer") from exc

    # Register cleanup as soon as each worker exists, including UI-build failures.
    with ExitStack() as resources:
        db = LocalDatabaseManager()
        camera = CameraGrabber(camera_index=camera_index,
                               allow_mock=bool(config.get("simulation", False)))
        resources.callback(_stop_resource, camera)
        engine = InferenceEngine()
        if not engine.engine_type.startswith("ONNX"):
            print("[WARNING] Real ONNX model is not ready; only unsaved preview is available.")
        worker = InferenceWorker(engine)
        resources.callback(_stop_resource, worker)
        worker.start()
        # Do not auto-open arbitrary COM ports or send this legacy vocabulary to
        # sensorless boards. The dual-board adapter is a separate integration gate.
        iot = ESP32SerialDriver(port=config.get("serial_port"))
        resources.callback(_stop_resource, iot)
        chamber = ChamberController(iot, camera, worker.frame_queue, worker.result_queue)
        resources.callback(_stop_resource, chamber)
        sync = BackgroundSyncWorker(db, os.getenv("API_BASE_URL", "http://localhost:8000"),
                                    os.getenv("API_KEY", ""))
        resources.callback(_stop_resource, sync)
        if not config.get("simulation", False):
            sync.start()
        app = OvaLensOperatorApp(camera=camera, engine=engine, iot=iot, db=db,
                                 sync_worker=sync, chamber=chamber,
                                 inference_worker=worker, device_id=device_id,
                                 startup_config=config)
        try:
            app.mainloop()
        finally:
            if hasattr(app, "_jobs"):
                app._jobs.close()


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.exit(1)
