from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np


@dataclass(frozen=True)
class FaceDetection:
    bbox_xyxy: tuple[int, int, int, int]
    landmarks_5: Optional[np.ndarray]
    score: float

    @property
    def bbox_xywh(self) -> list[int]:
        x1, y1, x2, y2 = self.bbox_xyxy
        return [x1, y1, x2 - x1, y2 - y1]


class FaceDetector:
    def __init__(self, model_path: str, device: str = "cpu"):
        try:
            from ultralytics import YOLO
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            raise RuntimeError(f"ultralytics is required for YOLOv8-Face detection: {exc}") from exc

        self.model_path = model_path
        self.device = device
        self.model = YOLO(model_path, task="pose")

    def detect(self, image_bgr: np.ndarray) -> FaceDetection | None:
        results = self.model(image_bgr, verbose=False, device=self.device)
        if not results or results[0].boxes is None or len(results[0].boxes) == 0:
            return None

        boxes = results[0].boxes.xyxy.cpu().numpy()
        scores = results[0].boxes.conf.cpu().numpy()
        best_idx = int(np.argmax(scores))

        h, w = image_bgr.shape[:2]
        x1, y1, x2, y2 = map(int, boxes[best_idx])
        x1 = max(0, min(w - 1, x1))
        y1 = max(0, min(h - 1, y1))
        x2 = max(x1 + 1, min(w, x2))
        y2 = max(y1 + 1, min(h, y2))

        landmarks = None
        if results[0].keypoints is not None:
            keypoints = results[0].keypoints.xy.cpu().numpy()
            if len(keypoints) > best_idx and keypoints[best_idx].shape[0] >= 5:
                landmarks = keypoints[best_idx][:5].astype(np.float32)

        return FaceDetection(
            bbox_xyxy=(x1, y1, x2, y2),
            landmarks_5=landmarks,
            score=float(scores[best_idx]),
        )


class FaceAligner:
    def __init__(self, output_size: tuple[int, int] = (112, 112)):
        self.output_size = output_size
        self._target = np.array(
            [
                [38.2946, 51.6963],
                [73.5318, 51.5014],
                [56.0252, 71.7366],
                [41.5493, 92.3655],
                [70.7299, 92.2041],
            ],
            dtype=np.float32,
        )

    def align(self, image_bgr: np.ndarray, detection: FaceDetection) -> np.ndarray:
        if detection.landmarks_5 is None:
            return self.crop(image_bgr, detection.bbox_xyxy)

        transform, _ = cv2.estimateAffinePartial2D(
            detection.landmarks_5.astype(np.float32),
            self._target,
            method=cv2.LMEDS,
        )
        if transform is None:
            return self.crop(image_bgr, detection.bbox_xyxy)

        return cv2.warpAffine(image_bgr, transform, self.output_size, flags=cv2.INTER_LINEAR)

    def crop(self, image_bgr: np.ndarray, bbox_xyxy: tuple[int, int, int, int]) -> np.ndarray:
        x1, y1, x2, y2 = bbox_xyxy
        crop = image_bgr[y1:y2, x1:x2]
        return cv2.resize(crop, self.output_size, interpolation=cv2.INTER_LINEAR)
