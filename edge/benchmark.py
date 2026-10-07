"""Repeatable model timing; synthetic frames do not measure sorting accuracy or camera latency."""
import argparse
import json
from pathlib import Path
import platform
import statistics
import time
import numpy as np
from src.core.inference import InferenceEngine
from src.core.settings import SettingsStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--frames", type=int, default=50)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--threads", type=int)
    args = parser.parse_args()
    if not 3 <= args.frames <= 10000:
        parser.error("frames must be between 3 and 10000")
    settings = SettingsStore().load()
    engine = InferenceEngine(conf_threshold=settings.detection.confidence, iou_threshold=settings.detection.iou,
                             intra_op_threads=args.threads)
    if not engine.engine_type.startswith("ONNX"):
        raise RuntimeError("Benchmark requires the real ONNX model; simulated timings would be misleading")
    engine.conf_threshold, engine.iou_threshold = settings.detection.confidence, settings.detection.iou
    image = np.zeros((settings.camera.height, settings.camera.width, 3), dtype=np.uint8)
    timings = []
    for _ in range(args.frames):
        start = time.perf_counter()
        engine.predict(image)
        timings.append((time.perf_counter() - start) * 1000)
    result = {"mode": "synthetic model timing only", "platform": platform.platform(),
              "engine": engine.engine_type, "frames": args.frames, "shape": list(image.shape),
              "intra_op_threads": engine.intra_op_threads,
              "median_ms": statistics.median(timings), "p95_ms": float(np.percentile(timings, 95)),
              "settings": settings.snapshot()}
    if args.baseline:
        baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
        result["baseline_p95_ms"] = baseline["p95_ms"]
        result["p95_change_percent"] = (result["p95_ms"] / baseline["p95_ms"] - 1) * 100
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
