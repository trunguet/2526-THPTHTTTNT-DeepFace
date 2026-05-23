from dataclasses import dataclass
from os import getenv


def _get_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class MinioSettings:
    endpoint: str = getenv("MINIO_ENDPOINT", "minio:9000")
    access_key: str = getenv("MINIO_ROOT_USER", "minioadmin")
    secret_key: str = getenv("MINIO_ROOT_PASSWORD", "minioadmin")
    bucket: str = getenv("MINIO_BUCKET", "deepface-images")
    secure: bool = _get_bool("MINIO_SECURE", False)


minio_settings = MinioSettings()


def get_minio_client():
    from minio import Minio

    return Minio(
        minio_settings.endpoint,
        access_key=minio_settings.access_key,
        secret_key=minio_settings.secret_key,
        secure=minio_settings.secure,
    )
