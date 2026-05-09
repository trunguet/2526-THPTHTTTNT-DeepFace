import unittest

import numpy as np

from app.ml.detector import FaceDetection
from app.ml.quality import QualityMetrics, compute_quality_metrics, reject_reason_from_metrics


class QualityGateTests(unittest.TestCase):
    def _reject(self, image_bgr: np.ndarray, bbox_xyxy: tuple[int, int, int, int]) -> str | None:
        detection = FaceDetection(bbox_xyxy=bbox_xyxy, landmarks_5=None, score=0.99)
        metrics = compute_quality_metrics(image_bgr, detection)
        return reject_reason_from_metrics(
            metrics,
            min_frame_brightness=35,
            min_face_brightness=45,
            # Mirror config defaults (approx 40–80cm).
            max_face_area_ratio=0.8,
            min_face_area_ratio=0.047,
            min_face_height_ratio=0.18,
            max_face_height_ratio=0.56,
            max_face_roll_deg=25,
            min_face_sharpness=60,
            max_head_yaw_deg=35,
            max_head_pitch_deg=30,
            enforce_pose_gate=False,
            bright_face_min=170,
            dark_bg_max=55,
            bright_face_dark_bg_ratio_min=3.0,
        )

    def test_reject_too_dark(self) -> None:
        img = np.zeros((100, 100, 3), dtype=np.uint8)
        self.assertEqual(self._reject(img, (25, 25, 75, 75)), "too_dark")

    def test_reject_face_too_close(self) -> None:
        img = np.full((100, 100, 3), 128, dtype=np.uint8)
        img[10:90:5, 10:90] = 200
        img[10:90, 10:90:5] = 40
        # Face bbox covers 81% of pixels -> too close for default 0.55.
        self.assertEqual(self._reject(img, (5, 5, 95, 95)), "face_too_close")

    def test_reject_face_bright_background_dark(self) -> None:
        img = np.zeros((120, 120, 3), dtype=np.uint8)
        img[40:80, 40:80] = 255
        self.assertEqual(self._reject(img, (40, 40, 80, 80)), "face_bright_bg_dark")

    def test_accept_reason_none(self) -> None:
        img = np.full((120, 120, 3), 120, dtype=np.uint8)
        # Add texture so Laplacian variance is non-trivial.
        img[35:85:4, 35:85] = 200
        img[35:85, 35:85:4] = 40
        self.assertIsNone(self._reject(img, (35, 35, 85, 85)))

    def test_reject_face_too_far(self) -> None:
        img = np.full((200, 200, 3), 128, dtype=np.uint8)
        img[80:120:5, 80:120] = 200
        img[80:120, 80:120:5] = 40
        # Face bbox height ratio 0.10 -> too far for default min 0.18.
        self.assertEqual(self._reject(img, (90, 90, 110, 110)), "face_too_far")

    def test_reject_too_blurry(self) -> None:
        img = np.full((120, 120, 3), 120, dtype=np.uint8)
        self.assertEqual(self._reject(img, (35, 35, 85, 85)), "too_blurry")

    def test_reject_face_tilted(self) -> None:
        img = np.full((120, 120, 3), 120, dtype=np.uint8)
        img[35:85:4, 35:85] = 200
        img[35:85, 35:85:4] = 40
        # Craft landmarks with ~45deg roll between eyes.
        landmarks = np.array(
            [
                [40, 40],  # left eye
                [60, 60],  # right eye
                [50, 55],  # nose
                [43, 70],  # left mouth
                [57, 70],  # right mouth
            ],
            dtype=np.float32,
        )
        detection = FaceDetection(bbox_xyxy=(35, 35, 85, 85), landmarks_5=landmarks, score=0.99)
        metrics = compute_quality_metrics(img, detection)
        reason = reject_reason_from_metrics(
            metrics,
            min_frame_brightness=35,
            min_face_brightness=45,
            max_face_area_ratio=0.8,
            min_face_area_ratio=0.047,
            min_face_height_ratio=0.18,
            max_face_height_ratio=0.56,
            max_face_roll_deg=25,
            min_face_sharpness=60,
            max_head_yaw_deg=35,
            max_head_pitch_deg=30,
            enforce_pose_gate=False,
            bright_face_min=170,
            dark_bg_max=55,
            bright_face_dark_bg_ratio_min=3.0,
        )
        self.assertEqual(reason, "face_tilted")

    def test_reject_face_turned_when_pose_gate_enabled(self) -> None:
        metrics = QualityMetrics(
            frame_mean=120.0,
            face_mean=120.0,
            background_mean=120.0,
            face_area_ratio=0.2,
            face_height_ratio=0.3,
            face_width_ratio=0.3,
            face_roll_deg=0.0,
            head_yaw_deg=45.0,
            head_pitch_deg=0.0,
            head_roll_deg=0.0,
            face_sharpness=200.0,
        )
        reason = reject_reason_from_metrics(
            metrics,
            min_frame_brightness=35,
            min_face_brightness=45,
            max_face_area_ratio=0.8,
            min_face_area_ratio=0.047,
            min_face_height_ratio=0.18,
            max_face_height_ratio=0.56,
            max_face_roll_deg=25,
            min_face_sharpness=60,
            max_head_yaw_deg=35,
            max_head_pitch_deg=30,
            enforce_pose_gate=True,
            bright_face_min=170,
            dark_bg_max=55,
            bright_face_dark_bg_ratio_min=3.0,
        )
        self.assertEqual(reason, "face_turned")


if __name__ == "__main__":
    unittest.main()
