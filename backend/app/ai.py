import base64
import io
from typing import Any

import numpy as np
from PIL import Image, ImageOps

from app.config import VECTOR_SIZE


def decode_base64_image(data_url: str) -> bytes:
    if "," in data_url:
        data_url = data_url.split(",", 1)[1]
    return base64.b64decode(data_url)


def validate_image(image_bytes: bytes) -> None:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image.verify()


def build_embedding(image_bytes: bytes) -> list[float]:
    with Image.open(io.BytesIO(image_bytes)) as image:
        image = ImageOps.exif_transpose(image)
        image = image.convert("L")
        side = int(VECTOR_SIZE ** 0.5)
        image = ImageOps.fit(image, (side, side), method=Image.Resampling.BILINEAR)
        vector = np.asarray(image, dtype=np.float32).reshape(-1)

    vector = vector / 255.0
    vector = vector - float(vector.mean())
    norm = float(np.linalg.norm(vector))
    if norm == 0:
        return vector.tolist()
    return (vector / norm).astype(np.float32).tolist()


def qdrant_score(result: Any) -> float:
    return float(getattr(result, "score", 0.0) or 0.0)
