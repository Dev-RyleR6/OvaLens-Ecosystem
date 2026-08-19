"""
OvaLens YOLOv8 ONNX Exporter
Exports PyTorch weights (best.pt) to optimized ONNX Runtime FP16 format for Raspberry Pi / PC edge deployment.
"""

import os
import sys
import argparse
from ultralytics import YOLO

DEFAULT_WEIGHTS_PATH = os.path.join(os.path.dirname(__file__), "weights", "best.pt")
DEFAULT_OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "weights")


def export_model(weights_path: str = DEFAULT_WEIGHTS_PATH, half: bool = True, imgsz: int = 640):
    if not os.path.exists(weights_path):
        print(f"[ERROR] Weights file not found: {weights_path}")
        sys.exit(1)

    print(f"[*] Loading YOLOv8 model from: {weights_path}")
    model = YOLO(weights_path)

    print(f"[*] Model Class Names: {model.names}")
    print(f"[*] Exporting to ONNX format (imgsz={imgsz}, half={half}, dynamic=False)...")

    # Export to ONNX
    onnx_path = model.export(
        format="onnx",
        imgsz=imgsz,
        half=half,
        dynamic=False,
        simplify=True
    )

    print(f"[SUCCESS] Model successfully exported to: {onnx_path}")
    return onnx_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export YOLOv8 model to optimized ONNX format")
    parser.add_argument("--weights", type=str, default=DEFAULT_WEIGHTS_PATH, help="Path to input .pt weights")
    parser.add_argument("--no-half", action="store_true", help="Disable FP16 half precision")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image dimension (default: 640)")
    args = parser.parse_args()

    export_model(weights_path=args.weights, half=(not args.no_half), imgsz=args.imgsz)
