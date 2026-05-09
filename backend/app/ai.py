import base64
import io
import hashlib
from dataclasses import asdict, is_dataclass

from PIL import Image

from app.ml.pipeline import VerificationResult, get_face_pipeline
from app.cache import get_json, set_json
from app.config import CACHE_VERIFY_TTL_SECONDS
from app.ml.anti_spoof import AntiSpoofResult as MiniFASResult
from app.ml.matcher import MatchResult


def decode_base64_image(data_url: str) -> bytes:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


def validate_image(image_bytes: bytes) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.verify()


def build_embedding(image_bytes: bytes) -> list[float]:
    result = get_face_pipeline().embedding_for_enroll(image_bytes)
    return result.embedding.astype("float32").tolist()


def verify_liveness_and_embedding(image_bytes: bytes) -> VerificationResult:
    ttl = int(CACHE_VERIFY_TTL_SECONDS)
    if ttl <= 0:
        return get_face_pipeline().verify(image_bytes)

    digest = hashlib.sha256(image_bytes).hexdigest()
    cache_key = f"cache:verify:{digest}"
    cached = get_json(cache_key)
    if isinstance(cached, dict) and "status" in cached and "reason" in cached:
        anti_spoof = None
        match = None
        if isinstance(cached.get("anti_spoof"), dict):
            try:
                anti_spoof = MiniFASResult(**cached["anti_spoof"])
            except Exception:
                anti_spoof = None
        if isinstance(cached.get("match"), dict):
            try:
                match = MatchResult(**cached["match"])
            except Exception:
                match = None

        # Rehydrate minimal VerificationResult fields used by API response.
        return VerificationResult(
            status=str(cached.get("status")),
            reason=str(cached.get("reason")),
            embedding=None,
            detection=None,
            anti_spoof=anti_spoof,
            match=match,
        )

    result = get_face_pipeline().verify(image_bytes)
    # Cache only small subset to avoid storing embeddings/images in cache.
    def to_jsonable(value):
        if value is None:
            return None
        if is_dataclass(value):
            return asdict(value)
        return value

    payload = {
        "status": result.status,
        "reason": result.reason,
        "anti_spoof": to_jsonable(result.anti_spoof),
        "match": to_jsonable(result.match),
    }
    set_json(cache_key, payload, ttl_seconds=ttl)
    return result
