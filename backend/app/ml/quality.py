from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

from app.ml.detector import FaceDetection


@dataclass(frozen=True)
class QualityMetrics:
    frame_mean: float
    face_mean: float
    background_mean: float
    face_area_ratio: float
    face_height_ratio: float
    face_width_ratio: float
    face_roll_deg: float | None
    head_yaw_deg: float | None
    head_pitch_deg: float | None
    head_roll_deg: float | None
    face_sharpness: float


def compute_quality_metrics(image_bgr: np.ndarray, detection: FaceDetection) -> QualityMetrics:
    h, w = image_bgr.shape[:2]
    if h <= 0 or w <= 0:
        raise ValueError("Invalid image shape")

    x1, y1, x2, y2 = detection.bbox_xyxy
    x1 = max(0, min(w - 1, int(x1)))
    y1 = max(0, min(h - 1, int(y1)))
    x2 = max(x1 + 1, min(w, int(x2)))
    y2 = max(y1 + 1, min(h, int(y2)))

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    total_pixels = float(h * w)
    total_sum = float(np.sum(gray, dtype=np.float64))
    frame_mean = total_sum / total_pixels

    face_gray = gray[y1:y2, x1:x2]
    face_pixels = float(face_gray.size)
    face_sum = float(np.sum(face_gray, dtype=np.float64))
    face_mean = face_sum / max(1.0, face_pixels)

    background_pixels = max(1.0, total_pixels - face_pixels)
    background_sum = total_sum - face_sum
    background_mean = background_sum / background_pixels

    face_area_ratio = face_pixels / total_pixels
    face_height_ratio = float((y2 - y1) / float(h))
    face_width_ratio = float((x2 - x1) / float(w))

    lap = cv2.Laplacian(face_gray, cv2.CV_64F)
    face_sharpness = float(lap.var())

    face_roll_deg: float | None = None
    if detection.landmarks_5 is not None and detection.landmarks_5.shape[0] >= 2:
        left_eye = detection.landmarks_5[0]
        right_eye = detection.landmarks_5[1]
        dx = float(right_eye[0] - left_eye[0])
        dy = float(right_eye[1] - left_eye[1])
        if dx != 0.0 or dy != 0.0:
            face_roll_deg = float(np.degrees(np.arctan2(dy, dx)))

    head_yaw_deg: float | None = None
    head_pitch_deg: float | None = None
    head_roll_deg: float | None = None
    if detection.landmarks_5 is not None and detection.landmarks_5.shape[0] >= 5:
        # Estimate head pose using a simple 3D face model and solvePnP.
        # Landmarks order (YOLOv8-face style in this repo): left_eye, right_eye, nose, left_mouth, right_mouth.
        image_points = detection.landmarks_5[:5].astype(np.float64)
        model_points = np.array(
            [
                (-30.0, 30.0, -30.0),  # left eye
                (30.0, 30.0, -30.0),  # right eye
                (0.0, 0.0, 0.0),  # nose tip
                (-25.0, -30.0, -30.0),  # left mouth
                (25.0, -30.0, -30.0),  # right mouth
            ],
            dtype=np.float64,
        )

        focal_length = float(w)
        center = (float(w) / 2.0, float(h) / 2.0)
        camera_matrix = np.array(
            [
                [focal_length, 0.0, center[0]],
                [0.0, focal_length, center[1]],
                [0.0, 0.0, 1.0],
            ],
            dtype=np.float64,
        )
        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # With 5 points, ITERATIVE may fail (needs >= 6 for its DLT init path in some OpenCV builds).
        ok, rvec, tvec = cv2.solvePnP(
            model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP,
        )
        if ok:
            rmat, _ = cv2.Rodrigues(rvec)
            # Convert rotation matrix to Euler angles (degrees).
            sy = float(np.sqrt(rmat[0, 0] * rmat[0, 0] + rmat[1, 0] * rmat[1, 0]))
            singular = sy < 1e-6
            if not singular:
                x = float(np.arctan2(rmat[2, 1], rmat[2, 2]))
                y = float(np.arctan2(-rmat[2, 0], sy))
                z = float(np.arctan2(rmat[1, 0], rmat[0, 0]))
            else:
                x = float(np.arctan2(-rmat[1, 2], rmat[1, 1]))
                y = float(np.arctan2(-rmat[2, 0], sy))
                z = 0.0

            head_pitch_deg = float(np.degrees(x))
            head_yaw_deg = float(np.degrees(y))
            head_roll_deg = float(np.degrees(z))

    return QualityMetrics(
        frame_mean=float(frame_mean),
        face_mean=float(face_mean),
        background_mean=float(background_mean),
        face_area_ratio=float(face_area_ratio),
        face_height_ratio=float(face_height_ratio),
        face_width_ratio=float(face_width_ratio),
        face_roll_deg=face_roll_deg,
        head_yaw_deg=head_yaw_deg,
        head_pitch_deg=head_pitch_deg,
        head_roll_deg=head_roll_deg,
        face_sharpness=float(face_sharpness),
    )


def reject_reason_from_metrics(
    metrics: QualityMetrics,
    *,
    min_frame_brightness: float,
    min_face_brightness: float,
    max_face_area_ratio: float,
    min_face_area_ratio: float,
    min_face_height_ratio: float,
    max_face_height_ratio: float,
    max_face_roll_deg: float,
    min_face_sharpness: float,
    max_head_yaw_deg: float,
    max_head_pitch_deg: float,
    enforce_pose_gate: bool,
    bright_face_min: float,
    dark_bg_max: float,
    bright_face_dark_bg_ratio_min: float,
) -> str | None:
    if (
        metrics.background_mean <= dark_bg_max
        and metrics.face_mean >= bright_face_min
        and (metrics.face_mean / (metrics.background_mean + 1.0)) >= bright_face_dark_bg_ratio_min
    ):
        return "face_bright_bg_dark"

    if metrics.frame_mean < min_frame_brightness or metrics.face_mean < min_face_brightness:
        return "too_dark"

    if metrics.face_roll_deg is not None and abs(metrics.face_roll_deg) > max_face_roll_deg:
        return "face_tilted"

    if metrics.face_sharpness < min_face_sharpness:
        return "too_blurry"

    if enforce_pose_gate and metrics.head_yaw_deg is not None and abs(metrics.head_yaw_deg) > max_head_yaw_deg:
        return "face_turned"

    if enforce_pose_gate and metrics.head_pitch_deg is not None and abs(metrics.head_pitch_deg) > max_head_pitch_deg:
        return "face_turned"

    # Distance gate: approximate 50–100cm constraint using bbox ratios.
    if metrics.face_height_ratio >= max_face_height_ratio or metrics.face_area_ratio >= max_face_area_ratio:
        return "face_too_close"

    if metrics.face_height_ratio <= min_face_height_ratio or metrics.face_area_ratio <= min_face_area_ratio:
        return "face_too_far"

    return None
