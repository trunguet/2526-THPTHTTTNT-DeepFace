import io
import time
from uuid import uuid4

from minio import Minio

from app.config import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
    PUBLIC_API_BASE_URL,
)


def get_minio_client() -> Minio:
    return Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False,
    )


def init_bucket(retries: int = 20) -> None:
    client = get_minio_client()
    for attempt in range(retries):
        try:
            if not client.bucket_exists(MINIO_BUCKET):
                client.make_bucket(MINIO_BUCKET)
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def object_url(object_key: str) -> str:
    return f"{PUBLIC_API_BASE_URL}/api/files/{object_key}"


def save_bytes(prefix: str, image_bytes: bytes, content_type: str = "image/jpeg") -> tuple[str, str]:
    object_key = f"{prefix}/{uuid4().hex}.jpg"
    client = get_minio_client()
    client.put_object(
        MINIO_BUCKET,
        object_key,
        io.BytesIO(image_bytes),
        length=len(image_bytes),
        content_type=content_type,
    )
    return object_key, object_url(object_key)


def read_bytes(object_key: str) -> bytes:
    client = get_minio_client()
    response = client.get_object(MINIO_BUCKET, object_key)
    try:
        return response.read()
    finally:
        response.close()
        response.release_conn()


def delete_object(object_key: str) -> None:
    if not object_key:
        return
    get_minio_client().remove_object(MINIO_BUCKET, object_key)
