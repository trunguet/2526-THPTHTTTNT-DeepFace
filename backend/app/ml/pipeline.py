from dataclasses import dataclass
import io

import cv2
import numpy as np

from app.config import (
    ANTISPOOF_DEVICE_ID,
    DETECTOR_MIN_SCORE,
    FACE_DEVICE,
    QUALITY_BRIGHT_FACE_DARK_BG_BG_MAX,
    QUALITY_BRIGHT_FACE_DARK_BG_FACE_MIN,
    QUALITY_BRIGHT_FACE_DARK_BG_RATIO_MIN,
    QUALITY_ENFORCE_POSE_GATE,
    QUALITY_MAX_FACE_AREA_RATIO,
    QUALITY_MAX_FACE_HEIGHT_RATIO,
    QUALITY_MIN_FACE_AREA_RATIO,
    QUALITY_MIN_FACE_BRIGHTNESS,
    QUALITY_MIN_FACE_HEIGHT_RATIO,
    QUALITY_MIN_FACE_SHARPNESS,
    QUALITY_MIN_FRAME_BRIGHTNESS,
    QUALITY_MAX_FACE_ROLL_DEG,
    QUALITY_MAX_FACE_PITCH_DEG,
    QUALITY_MAX_FACE_YAW_DEG,
    YOLO_FACE_MODEL,
)
from app.ml.anti_spoof import AntiSpoofResult, MiniFASNetAntiSpoofing
from app.ml.detector import FaceAligner, FaceDetection, FaceDetector
from app.ml.embedder import ArcFaceEmbedder
from app.ml.matcher import MatchResult, QdrantFaceMatcher
from app.ml.quality import compute_quality_metrics, reject_reason_from_metrics


@dataclass(frozen=True)
class EmbeddingResult:
    embedding: np.ndarray
    detection: FaceDetection


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str
    embedding: np.ndarray | None
    detection: FaceDetection | None
    anti_spoof: AntiSpoofResult | None
    match: MatchResult | None


class FaceRecognitionPipeline:
    def __init__(self) -> None:
        self.detector = FaceDetector(YOLO_FACE_MODEL, device=FACE_DEVICE)
        self.aligner = FaceAligner()
        self.anti_spoof = MiniFASNetAntiSpoofing(device_id=ANTISPOOF_DEVICE_ID)
        self.embedder = ArcFaceEmbedder()
        self.matcher = QdrantFaceMatcher()

    def embedding_for_enroll(self, image_bytes: bytes) -> EmbeddingResult:
        image_bgr = decode_image_bytes(image_bytes)
        detections = [d for d in self.detector.detect_all(image_bgr) if d.score >= DETECTOR_MIN_SCORE]
        if not detections:
            raise ValueError("No face detected in employee image")
        if len(detections) > 1:
            raise ValueError("Multiple faces detected in employee image")
        detection = detections[0]

        aligned_face = self.aligner.align(image_bgr, detection)
        embedding = self.embedder.embed(aligned_face)
        return EmbeddingResult(embedding=embedding, detection=detection)

    def verify(self, image_bytes: bytes) -> VerificationResult:
        image_bgr = decode_image_bytes(image_bytes)
        detections = [d for d in self.detector.detect_all(image_bgr) if d.score >= DETECTOR_MIN_SCORE]
        if not detections:
            return VerificationResult(
                status="rejected",
                reason="no_face",
                embedding=None,
                detection=None,
                anti_spoof=None,
                match=None,
            )
        if len(detections) > 1:
            return VerificationResult(
                status="rejected",
                reason="multiple_faces",
                embedding=None,
                detection=detections[0],
                anti_spoof=None,
                match=None,
            )

        detection = detections[0]

        metrics = compute_quality_metrics(image_bgr, detection)
        quality_reject = reject_reason_from_metrics(
            metrics,
            min_frame_brightness=QUALITY_MIN_FRAME_BRIGHTNESS,
            min_face_brightness=QUALITY_MIN_FACE_BRIGHTNESS,
            max_face_area_ratio=QUALITY_MAX_FACE_AREA_RATIO,
            min_face_area_ratio=QUALITY_MIN_FACE_AREA_RATIO,
            min_face_height_ratio=QUALITY_MIN_FACE_HEIGHT_RATIO,
            max_face_height_ratio=QUALITY_MAX_FACE_HEIGHT_RATIO,
            max_face_roll_deg=QUALITY_MAX_FACE_ROLL_DEG,
            min_face_sharpness=QUALITY_MIN_FACE_SHARPNESS,
            max_head_yaw_deg=QUALITY_MAX_FACE_YAW_DEG,
            max_head_pitch_deg=QUALITY_MAX_FACE_PITCH_DEG,
            enforce_pose_gate=QUALITY_ENFORCE_POSE_GATE,
            bright_face_min=QUALITY_BRIGHT_FACE_DARK_BG_FACE_MIN,
            dark_bg_max=QUALITY_BRIGHT_FACE_DARK_BG_BG_MAX,
            bright_face_dark_bg_ratio_min=QUALITY_BRIGHT_FACE_DARK_BG_RATIO_MIN,
        )
        if quality_reject is not None:
            return VerificationResult(
                status="rejected",
                reason=quality_reject,
                embedding=None,
                detection=detection,
                anti_spoof=None,
                match=None,
            )

        spoof = self.anti_spoof.predict(image_bgr, detection)
        if not spoof.is_real:
            reason = (
                "minifas_low_score"
                if spoof.real_score < getattr(self.anti_spoof, "real_threshold", 0.5)
                else "spoof"
            )
            return VerificationResult(
                status="rejected",
                reason=reason,
                embedding=None,
                detection=detection,
                anti_spoof=spoof,
                match=None,
            )

        aligned_face = self.aligner.align(image_bgr, detection)
        embedding = self.embedder.embed(aligned_face)
        match = self.matcher.match(embedding)
        if not match.matched:
            return VerificationResult(
                status="rejected",
                reason="no_match",
                embedding=embedding,
                detection=detection,
                anti_spoof=spoof,
                match=match,
            )

        return VerificationResult(
            status="accepted",
            reason="matched",
            embedding=embedding,
            detection=detection,
            anti_spoof=spoof,
            match=match,
        )


_pipeline: FaceRecognitionPipeline | None = None


def get_face_pipeline() -> FaceRecognitionPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = FaceRecognitionPipeline()
    return _pipeline


def decode_image_bytes(image_bytes: bytes) -> np.ndarray:
    array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image")
    return image


def encode_jpeg(image_bgr: np.ndarray) -> bytes:
    ok, buffer = cv2.imencode(".jpg", image_bgr)
    if not ok:
        raise ValueError("Failed to encode image")
    return bytes(buffer)


def image_bytes_from_array(image_bgr: np.ndarray) -> bytes:
    return encode_jpeg(image_bgr)


def image_bytes_from_pil_save(image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG")
    return buffer.getvalue()
