from dataclasses import dataclass
import os
import sys

import numpy as np
import cv2

from app.config import ANTISPOOF_REAL_THRESHOLD, FAS_BBOX_PAD_RATIO, FAS_MODEL_DIR, MINIFAS_CORE_DIR
from app.ml.detector import FaceDetection


@dataclass(frozen=True)
class AntiSpoofResult:
    is_real: bool
    confidence: float
    real_score: float
    spoof_score: float
    model_scores: dict[str, dict[str, float]]


class MiniFASNetAntiSpoofing:
    def __init__(
        self,
        model_dir: str = FAS_MODEL_DIR,
        minifas_core_dir: str = MINIFAS_CORE_DIR,
        device_id: int = 0,
        real_threshold: float = ANTISPOOF_REAL_THRESHOLD,
    ):
        if minifas_core_dir not in sys.path:
            sys.path.insert(0, minifas_core_dir)

        try:
            from src.anti_spoof_predict import AntiSpoofPredict
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            raise RuntimeError(f"MiniFASNet anti-spoofing import failed: {exc}") from exc

        self.predictor = AntiSpoofPredict(device_id)
        self.model_dir = model_dir
        self.real_threshold = real_threshold

    def predict(self, image_bgr: np.ndarray, detection: FaceDetection) -> AntiSpoofResult:
        model_files = sorted(f for f in os.listdir(self.model_dir) if f.endswith(".pth"))
        if not model_files:
            raise RuntimeError(f"No MiniFASNet .pth files found in {self.model_dir}")

        prediction = np.zeros((1, 3), dtype=np.float32)
        scores: dict[str, dict[str, float]] = {}

        input_image = image_bgr
        x1, y1, x2, y2 = detection.bbox_xyxy
        h_img, w_img = image_bgr.shape[:2]
        pad_x = int(round((x2 - x1) * FAS_BBOX_PAD_RATIO))
        pad_y = int(round((y2 - y1) * FAS_BBOX_PAD_RATIO))
        x1p = max(0, x1 - pad_x)
        y1p = max(0, y1 - pad_y)
        x2p = min(w_img, x2 + pad_x)
        y2p = min(h_img, y2 + pad_y)
        bbox_xywh = [x1p, y1p, max(1, x2p - x1p), max(1, y2p - y1p)]
        if detection.landmarks_5 is not None and detection.landmarks_5.shape[0] >= 2:
            left_eye = detection.landmarks_5[0]
            right_eye = detection.landmarks_5[1]
            dx = float(right_eye[0] - left_eye[0])
            dy = float(right_eye[1] - left_eye[1])
            if dx != 0.0 or dy != 0.0:
                angle_deg = float(np.degrees(np.arctan2(dy, dx)))
                # Only correct reasonable roll angles to avoid over-warping on noisy landmarks.
                if abs(angle_deg) >= 5.0 and abs(angle_deg) <= 45.0:
                    x1, y1, x2, y2 = detection.bbox_xyxy
                    cx = (x1 + x2) / 2.0
                    cy = (y1 + y2) / 2.0
                    rot = cv2.getRotationMatrix2D((cx, cy), -angle_deg, 1.0)
                    h, w = image_bgr.shape[:2]
                    input_image = cv2.warpAffine(
                        image_bgr,
                        rot,
                        (w, h),
                        flags=cv2.INTER_LINEAR,
                        borderMode=cv2.BORDER_REFLECT_101,
                    )

                    # Rotate padded bbox corners.
                    corners = np.array(
                        [[x1p, y1p], [x2p, y1p], [x2p, y2p], [x1p, y2p]],
                        dtype=np.float32,
                    )
                    ones = np.ones((corners.shape[0], 1), dtype=np.float32)
                    corners_h = np.concatenate([corners, ones], axis=1)
                    warped = corners_h @ rot.T
                    x_min = float(np.min(warped[:, 0]))
                    y_min = float(np.min(warped[:, 1]))
                    x_max = float(np.max(warped[:, 0]))
                    y_max = float(np.max(warped[:, 1]))
                    x_min = max(0, min(w - 1, int(round(x_min))))
                    y_min = max(0, min(h - 1, int(round(y_min))))
                    x_max = max(x_min + 1, min(w, int(round(x_max))))
                    y_max = max(y_min + 1, min(h, int(round(y_max))))
                    bbox_xywh = [x_min, y_min, x_max - x_min, y_max - y_min]

        for model_file in model_files:
            model_path = os.path.join(self.model_dir, model_file)
            result = self.predictor.predict(input_image, model_path, bbox=bbox_xywh)
            prediction += result
            spoof_score = float(result[0][0])
            real_score = float(result[0][1])
            scores[model_file] = {
                "real": real_score,
                "spoof": spoof_score,
            }

        prediction = prediction / len(model_files)
        label = int(np.argmax(prediction))
        real_score = float(prediction[0][1])
        spoof_score = float(prediction[0][0])
        confidence = float(prediction[0][label])
        is_real = label == 1 and real_score >= self.real_threshold

        return AntiSpoofResult(
            is_real=is_real,
            confidence=confidence,
            real_score=real_score,
            spoof_score=spoof_score,
            model_scores=scores,
        )
