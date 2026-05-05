from dataclasses import dataclass
import io

import cv2
import numpy as np

from app.config import (
    ANTISPOOF_DEVICE_ID,
    FACE_DEVICE,
    YOLO_FACE_MODEL,
)
from app.ml.anti_spoof import AntiSpoofResult, MiniFASNetAntiSpoofing
from app.ml.detector import FaceAligner, FaceDetection, FaceDetector
from app.ml.embedder import ArcFaceEmbedder
from app.ml.matcher import MatchResult, QdrantFaceMatcher


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
        detection = self.detector.detect(image_bgr)
        if detection is None:
            raise ValueError("No face detected in employee image")

        aligned_face = self.aligner.align(image_bgr, detection)
        embedding = self.embedder.embed(aligned_face)
        return EmbeddingResult(embedding=embedding, detection=detection)

    def verify(self, image_bytes: bytes) -> VerificationResult:
        image_bgr = decode_image_bytes(image_bytes)
        detection = self.detector.detect(image_bgr)
        if detection is None:
            return VerificationResult(
                status="rejected",
                reason="no_face",
                embedding=None,
                detection=None,
                anti_spoof=None,
                match=None,
            )

        spoof = self.anti_spoof.predict(image_bgr, detection)
        if not spoof.is_real:
            return VerificationResult(
                status="rejected",
                reason="spoof",
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
