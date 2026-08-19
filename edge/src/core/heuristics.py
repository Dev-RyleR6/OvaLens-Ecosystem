"""
Candling Heuristics & Optical Quality Verification
Ensures egg detections satisfy biological geometry and optical luminance constraints.
"""

from typing import Tuple, Optional, Dict, Any
import numpy as np
import cv2


class CandlingHeuristics:
    MIN_ASPECT_RATIO = 0.65
    MAX_ASPECT_RATIO = 1.45
    MIN_CANDLING_LUMINANCE = 35.0  # Minimum average brightness in candling aperture
    MIN_EGG_AREA_PX = 4000         # Minimum pixel area for a valid duck egg

    @staticmethod
    def validate_aspect_ratio(w: float, h: float) -> bool:
        """Validate duck egg geometric aspect ratio."""
        if h <= 0 or w <= 0:
            return False
        ar = float(w) / float(h)
        return CandlingHeuristics.MIN_ASPECT_RATIO <= ar <= CandlingHeuristics.MAX_ASPECT_RATIO

    @staticmethod
    def calculate_candling_luminance(frame: np.ndarray, bbox_norm: Tuple[float, float, float, float]) -> Dict[str, float]:
        """
        Calculate optical candling metrics (mean V-channel brightness & variance)
        bbox_norm: (x_center, y_center, width, height) in 0..1 coordinates.
        """
        h_img, w_img = frame.shape[:2]
        xc, yc, w, h = bbox_norm

        x1 = max(0, int((xc - w / 2.0) * w_img))
        y1 = max(0, int((yc - h / 2.0) * h_img))
        x2 = min(w_img, int((xc + w / 2.0) * w_img))
        y2 = min(h_img, int((yc + h / 2.0) * h_img))

        if x2 <= x1 or y2 <= y1:
            return {"mean_luminance": 0.0, "std_luminance": 0.0, "area_px": 0}

        roi = frame[y1:y2, x1:x2]
        hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)
        v_channel = hsv[:, :, 2]

        mean_v = float(np.mean(v_channel))
        std_v = float(np.std(v_channel))
        area_px = int((x2 - x1) * (y2 - y1))

        return {
            "mean_luminance": round(mean_v, 2),
            "std_luminance": round(std_v, 2),
            "area_px": area_px
        }

    @classmethod
    def filter_and_rank_detections(cls, detections: list, frame: np.ndarray) -> Optional[Dict[str, Any]]:
        """
        Filters and selects the best primary egg candidate in the candling zone.
        Detections format: list of dicts with {'bbox': [xc, yc, w, h], 'confidence': float, 'class': str}
        """
        if not detections:
            return None

        valid_candidates = []
        for det in detections:
            xc, yc, w, h = det["bbox"]
            conf = det["confidence"]
            cls_name = det["class"]

            # 1. Aspect ratio check
            if not cls.validate_aspect_ratio(w, h):
                continue

            # 2. Optical luminance check
            lum_info = cls.calculate_candling_luminance(frame, (xc, yc, w, h))
            if lum_info["mean_luminance"] < cls.MIN_CANDLING_LUMINANCE:
                continue

            # Calculate centrality score (closer to center = higher priority)
            dist_from_center = np.sqrt((xc - 0.5) ** 2 + (yc - 0.5) ** 2)
            centrality_weight = max(0.0, 1.0 - dist_from_center)

            total_score = (conf * 0.7) + (centrality_weight * 0.3)

            valid_candidates.append({
                **det,
                "score": total_score,
                "luminance": lum_info["mean_luminance"],
                "area_px": lum_info["area_px"]
            })

        if not valid_candidates:
            # Fall back to highest confidence raw detection if none passed strict filter
            return max(detections, key=lambda d: d["confidence"])

        # Return candidate with highest combined score
        return max(valid_candidates, key=lambda d: d["score"])
