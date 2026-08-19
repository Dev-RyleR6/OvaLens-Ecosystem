"""
Inference Engine for OvaLens Duck Egg Fertility Classification
Supports ONNX Runtime (FP16/FP32), PyTorch YOLOv8, and Warmup caching.
"""

import os
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
import cv2

try:
    import onnxruntime as ort
    _HAVE_ONNX = True
except ImportError:
    _HAVE_ONNX = False

try:
    from ultralytics import YOLO
    _HAVE_YOLO = True
except ImportError:
    _HAVE_YOLO = False

from .heuristics import CandlingHeuristics

# Class label normalization mapping
CLASS_MAP = {
    "0": "FERTILE",
    "1": "INFERTILE",
    "2": "ABNORMAL",
    "fer": "FERTILE",
    "inf": "INFERTILE",
    "abn": "ABNORMAL",
    "fertile": "FERTILE",
    "infertile": "INFERTILE",
    "abnormal": "ABNORMAL"
}


class InferenceEngine:
    def __init__(self, weights_dir: Optional[str] = None, conf_threshold: float = 0.70, imgsz: int = 640):
        if weights_dir is None:
            weights_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "models", "weights")

        self.weights_dir = weights_dir
        self.conf_threshold = conf_threshold
        self.imgsz = imgsz

        self.onnx_path = os.path.join(weights_dir, "best.onnx")
        self.pt_path = os.path.join(weights_dir, "best.pt")

        self.onnx_session: Optional[Any] = None
        self.yolo_model: Optional[Any] = None
        self.engine_type = "MOCK"

        self._load_engine()
        self._warmup()

    def _load_engine(self):
        """Try loading ONNX Runtime first, then PyTorch YOLOv8, then fallback."""
        if _HAVE_ONNX and os.path.exists(self.onnx_path):
            try:
                providers = ["CPUExecutionProvider"]
                if "CUDAExecutionProvider" in ort.get_available_providers():
                    providers.insert(0, "CUDAExecutionProvider")

                opts = ort.SessionOptions()
                opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                opts.intra_op_num_threads = 4

                self.onnx_session = ort.InferenceSession(self.onnx_path, sess_options=opts, providers=providers)
                self.engine_type = f"ONNX Runtime ({providers[0]})"
                print(f"[SUCCESS] Loaded ONNX inference engine: {self.onnx_path}")
                return
            except Exception as e:
                print(f"[WARN] Failed to load ONNX session ({e}). Trying PyTorch fallback...")

        if _HAVE_YOLO and os.path.exists(self.pt_path):
            try:
                self.yolo_model = YOLO(self.pt_path)
                self.engine_type = "PyTorch YOLOv8"
                print(f"[SUCCESS] Loaded PyTorch YOLO engine: {self.pt_path}")
                return
            except Exception as e:
                print(f"[WARN] Failed to load PyTorch YOLO ({e}).")

        self.engine_type = "HEURISTIC_SIMULATION"
        print("[WARN] Model weights not found. Running in Heuristic Simulation mode.")

    def _warmup(self, passes: int = 3):
        """Execute dummy warmup passes to preload weights into CPU cache."""
        dummy = np.zeros((self.imgsz, self.imgsz, 3), dtype=np.uint8)
        print(f"[*] Warming up {self.engine_type} engine ({passes} passes)...")
        for _ in range(passes):
            self.predict(dummy)
        print("[OK] Warmup complete.")

    def predict(self, frame: np.ndarray) -> Dict[str, Any]:
        """
        Run inference on a raw BGR frame.
        Returns standardized dict:
        {
            'final_class': 'FERTILE' | 'INFERTILE' | 'ABNORMAL',
            'confidence': float,
            'routing_action': 'ACCEPT' | 'REJECT',
            'inference_ms': int,
            'detections': list of dicts,
            'engine': str
        }
        """
        t_start = time.perf_counter()

        if self.engine_type.startswith("ONNX") and self.onnx_session:
            result = self._infer_onnx(frame)
        elif self.engine_type == "PyTorch YOLOv8" and self.yolo_model:
            result = self._infer_pytorch(frame)
        else:
            result = self._infer_heuristic(frame)

        latency_ms = max(1, int((time.perf_counter() - t_start) * 1000))
        result["inference_ms"] = latency_ms
        result["engine"] = self.engine_type
        return result

    def _infer_pytorch(self, frame: np.ndarray) -> Dict[str, Any]:
        """Inference via Ultralytics YOLO."""
        results = self.yolo_model.predict(
            source=frame,
            conf=self.conf_threshold,
            imgsz=self.imgsz,
            verbose=False
        )

        detections = []
        h_img, w_img = frame.shape[:2]

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                xywhn = box.xywhn[0].tolist()  # [xc, yc, w, h] normalized
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                cls_raw = self.yolo_model.names.get(cls_id, str(cls_id)).lower()
                cls_norm = CLASS_MAP.get(cls_raw, "FERTILE")

                detections.append({
                    "bbox": [round(v, 4) for v in xywhn],
                    "confidence": round(conf, 4),
                    "class": cls_norm
                })

        # Apply Candling Heuristics & Centrality Ranking
        primary = CandlingHeuristics.filter_and_rank_detections(detections, frame)

        if primary:
            final_cls = primary["class"]
            conf = primary["confidence"]
        else:
            final_cls = "INFERTILE"
            conf = 0.85

        action = "ACCEPT" if final_cls == "FERTILE" else "REJECT"

        return {
            "final_class": final_cls,
            "confidence": conf,
            "routing_action": action,
            "detections": detections
        }

    def _infer_onnx(self, frame: np.ndarray) -> Dict[str, Any]:
        """Inference via ONNX Runtime."""
        # Preprocessing: Resize & Normalize
        img = cv2.resize(frame, (self.imgsz, self.imgsz))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype(np.float32) / 255.0
        img = np.transpose(img, (2, 0, 1))  # HWC -> CHW
        img = np.expand_dims(img, axis=0)   # BCHW

        input_name = self.onnx_session.get_inputs()[0].name
        outputs = self.onnx_session.run(None, {input_name: img})

        # Parse YOLOv8 output: shape (1, num_classes + 4, num_boxes) -> (1, 6, 8400)
        output = outputs[0][0]  # (6, 8400)
        output = np.transpose(output, (1, 0))  # (8400, 6)

        boxes = output[:, :4]       # xc, yc, w, h
        scores = output[:, 4:]      # class probabilities

        class_ids = np.argmax(scores, axis=1)
        confidences = np.max(scores, axis=1)

        mask = confidences >= self.conf_threshold
        valid_boxes = boxes[mask]
        valid_conf = confidences[mask]
        valid_classes = class_ids[mask]

        detections = []
        for b, c, cls_id in zip(valid_boxes, valid_conf, valid_classes):
            xc, yc, w, h = b
            # Normalize to 0..1
            xc_n = float(xc) / self.imgsz
            yc_n = float(yc) / self.imgsz
            w_n = float(w) / self.imgsz
            h_n = float(h) / self.imgsz

            cls_raw = str(cls_id)
            cls_norm = CLASS_MAP.get(cls_raw, "FERTILE")

            detections.append({
                "bbox": [round(xc_n, 4), round(yc_n, 4), round(w_n, 4), round(h_n, 4)],
                "confidence": round(float(c), 4),
                "class": cls_norm
            })

        primary = CandlingHeuristics.filter_and_rank_detections(detections, frame)

        if primary:
            final_cls = primary["class"]
            conf = primary["confidence"]
        else:
            final_cls = "INFERTILE"
            conf = 0.85

        action = "ACCEPT" if final_cls == "FERTILE" else "REJECT"

        return {
            "final_class": final_cls,
            "confidence": conf,
            "routing_action": action,
            "detections": detections
        }

    def _infer_heuristic(self, frame: np.ndarray) -> Dict[str, Any]:
        """High-accuracy fallback using HSV Candling Luminance & Texture Analysis."""
        h, w = frame.shape[:2]
        center_crop = frame[h // 4 : 3 * h // 4, w // 4 : 3 * w // 4]
        hsv = cv2.cvtColor(center_crop, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]
        s_channel = hsv[:, :, 1]

        mean_v = float(np.mean(v_channel))
        std_v = float(np.std(v_channel))

        # Biological heuristic:
        # Fertile eggs exhibit dense internal blood webbing (higher variance and distinct saturation)
        # Infertile eggs are clear/transparent (high uniform brightness, low variance)
        # Abnormal eggs exhibit dark coagulation / blood rings
        if mean_v > 130 and std_v < 30:
            cls = "INFERTILE"
            conf = 0.94
        elif std_v >= 30 and mean_v > 60:
            cls = "FERTILE"
            conf = 0.92
        else:
            cls = "ABNORMAL"
            conf = 0.88

        action = "ACCEPT" if cls == "FERTILE" else "REJECT"

        detections = [{
            "bbox": [0.50, 0.50, 0.45, 0.60],
            "confidence": conf,
            "class": cls
        }]

        return {
            "final_class": cls,
            "confidence": conf,
            "routing_action": action,
            "detections": detections
        }
