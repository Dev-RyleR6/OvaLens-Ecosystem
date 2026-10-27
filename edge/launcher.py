"""OvaLens desktop launcher: explicit preview, no unvalidated hardware motion."""
import os
import sys

# Select Python before dotenv, serial, Tk or other third-party modules are loaded.
sys.path.insert(0, os.path.dirname(__file__))
if __name__ == "__main__":
    from project_runtime import restart_in_project_environment, check_runtime
    runtime_exit = restart_in_project_environment(__file__)
    if runtime_exit is not None:
        raise SystemExit(runtime_exit)
    if "--check-runtime" in sys.argv[1:]:
        raise SystemExit(check_runtime())

import platform
from contextlib import ExitStack
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from src.ui.startup_config import show_startup_config
from src.core.camera import CameraGrabber
from src.core.inference import InferenceEngine
from src.core.inference_worker import InferenceWorker
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp
from src.core.station import EdgeStation


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
    db = LocalDatabaseManager()
    config = show_startup_config(device_id=device_id, operator_name=db.get_batch_preferences().get("operator", ""))
    if config is None:
        print("[EXIT] Startup cancelled.")
        return
    try:
        camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    except ValueError as exc:
        raise ValueError("CAMERA_INDEX must be an integer") from exc

    # Register cleanup as soon as each worker exists, including UI-build failures.
    with ExitStack() as resources:
        camera = CameraGrabber(camera_index=camera_index,
                               allow_mock=bool(config.get("simulation", False)))
        resources.callback(_stop_resource, camera)
        engine = InferenceEngine()
        if not engine.engine_type.startswith("ONNX"):
            print("[WARNING] Real ONNX model is not ready; only unsaved preview is available.")
        worker = InferenceWorker(engine)
        resources.callback(_stop_resource, worker)
        worker.start()
        station = EdgeStation(camera, worker, db, device_id)
        if not station.store.path.exists():
            station.settings.camera.index = camera_index
            station.settings.validate()
        camera.initial_settings = station.settings.camera
        camera.camera_index = station.settings.camera.index
        camera.width, camera.height, camera.fps = (station.settings.camera.width,
            station.settings.camera.height, station.settings.camera.fps)
        engine.conf_threshold = station.settings.detection.confidence
        engine.iou_threshold = station.settings.detection.iou
        resources.callback(_stop_resource, station)
        sync = BackgroundSyncWorker(db, os.getenv("API_BASE_URL", "http://localhost:8000"),
                                    os.getenv("API_KEY", ""), device_id=device_id,
                                    device_name=os.getenv("DEVICE_NAME", device_id),
                                    hardware_platform=f"{platform.system()} {platform.machine()}",
                                    model_version=engine.engine_type)
        resources.callback(_stop_resource, sync)
        if not config.get("simulation", False):
            sync.start()
        app = OvaLensOperatorApp(camera=camera, engine=engine, station=station,
                                 db=db, sync_worker=sync,
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
