import base64
import io

from PIL import Image

from app.ml.pipeline import VerificationResult, get_face_pipeline


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
    return get_face_pipeline().verify(image_bytes)
