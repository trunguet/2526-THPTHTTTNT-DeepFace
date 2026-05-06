import base64
from dataclasses import dataclass
import io

import numpy as np
from PIL import Image

from app.ml.matcher import MatchResult, QdrantFaceMatcher


@dataclass(frozen=True)
class VerificationResult:
    status: str
    reason: str
    embedding: np.ndarray | None
    detection: None
    anti_spoof: None
    match: MatchResult | None


def decode_base64_image(data_url: str) -> bytes:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


def validate_image(image_bytes: bytes) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.verify()


def build_embedding(image_bytes: bytes) -> list[float]:
    image = Image.open(io.BytesIO(image_bytes)).convert("L").resize((32, 16))
    vector = np.asarray(image, dtype=np.float32).reshape(-1)
    vector = vector - float(vector.mean())
    std = float(vector.std())
    if std > 0:
        vector = vector / std
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        raise ValueError("Image has no usable visual features")
    return (vector / norm).astype(np.float32).tolist()


def verify_liveness_and_embedding(image_bytes: bytes) -> VerificationResult:
    embedding = np.asarray(build_embedding(image_bytes), dtype=np.float32)
    match = QdrantFaceMatcher().match(embedding)
    if match.matched:
        return VerificationResult(
            status="accepted",
            reason="matched",
            embedding=embedding,
            detection=None,
            anti_spoof=None,
            match=match,
        )

    return VerificationResult(
        status="rejected",
        reason="no_match",
        embedding=embedding,
        detection=None,
        anti_spoof=None,
        match=match,
    )
