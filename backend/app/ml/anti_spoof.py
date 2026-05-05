from dataclasses import dataclass
import os
import sys

import numpy as np

from app.config import ANTISPOOF_REAL_THRESHOLD, FAS_MODEL_DIR, MINIFAS_CORE_DIR
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
        bbox_xywh = detection.bbox_xywh

        for model_file in model_files:
            model_path = os.path.join(self.model_dir, model_file)
            result = self.predictor.predict(image_bgr, model_path, bbox=bbox_xywh)
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
