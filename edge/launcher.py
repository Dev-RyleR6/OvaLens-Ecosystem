"""
OvaLens Edge Operator Launcher
Bootstraps the quad-thread CV pipeline and CustomTkinter desktop interface.
"""

import os
import sys
from dotenv import load_dotenv

# Ensure edge root is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

# Load edge .env
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    load_dotenv(env_path)

from src.core.camera import CameraGrabber
from src.core.inference import InferenceEngine
from src.iot.serial_driver import ESP32SerialDriver
from src.db.local_db import LocalDatabaseManager
from src.sync.sync_worker import BackgroundSyncWorker
from src.ui.app import OvaLensOperatorApp


def main():
    print("=" * 65)
    print("   OVALENS EDGE OPERATOR SYSTEM — FOUNDATION UNIVERSITY")
    print("=" * 65)

    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    api_key = os.getenv("API_KEY", "dev-api-key-123")
    device_id = os.getenv("DEVICE_ID", "STATION-01-RP5")
    camera_index = int(os.getenv("CAMERA_INDEX", "0"))
    serial_port = os.getenv("SERIAL_PORT", None)

    # 1. Initialize Local Database Manager (SQLite WAL)
    print("\n[1/5] Initializing Local SQLite WAL Storage...")
    db_manager = LocalDatabaseManager()
    print("  [OK] Local database ready.")

    # 2. Initialize Camera Grabber
    print("\n[2/5] Initializing Camera Stream...")
    camera = CameraGrabber(camera_index=camera_index)
    camera.start()
    print("  [OK] Camera thread started.")

    # 3. Initialize AI Vision Inference Engine (ONNX Runtime / PyTorch)
    print("\n[3/5] Initializing AI Inference Engine...")
    engine = InferenceEngine()
    print(f"  [OK] Inference engine ready ({engine.engine_type}).")

    # 4. Initialize ESP32 Microcontroller Serial Driver
    print("\n[4/5] Initializing ESP32 Serial Driver...")
    iot = ESP32SerialDriver(port=serial_port)
    iot.start()

    # 5. Initialize Background Network Sync Worker
    print("\n[5/5] Initializing Background Sync Worker...")
    sync_worker = BackgroundSyncWorker(db_manager=db_manager, api_base_url=api_base_url, api_key=api_key)
    sync_worker.start()
    print("  [OK] Background sync worker started.")

    # 6. Launch CustomTkinter Desktop Application
    print("\n[START] Launching Operator GUI...")
    app = OvaLensOperatorApp(
        camera=camera,
        engine=engine,
        iot=iot,
        db=db_manager,
        sync_worker=sync_worker,
        device_id=device_id
    )

    def on_closing():
        print("\n[*] Shutting down OvaLens Edge Subsystems...")
        camera.stop()
        iot.stop()
        sync_worker.stop()
        app.destroy()
        print("[OK] Graceful shutdown complete.")

    app.protocol("WM_DELETE_WINDOW", on_closing)
    app.mainloop()


if __name__ == "__main__":
    main()
