from dataclasses import dataclass
from typing import BinaryIO

from fastapi import UploadFile

from app.config.minio import get_minio_client, minio_settings
from app.utils.image_utils import ImageValidationError, validate_image_upload


UnsupportedImageTypeError = ImageValidationError


@dataclass(frozen=True)
class StoredImage:
    object_key: str
    bucket: str
    content_type: str
    size: int


def ensure_bucket_exists() -> None:
    client = get_minio_client()
    if not client.bucket_exists(minio_settings.bucket):
        client.make_bucket(minio_settings.bucket)


def upload_image_file(
    file_obj: BinaryIO,
    *,
    filename: str,
    prefix: str,
    content_type: str | None = None,
) -> StoredImage:
    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)
    metadata = validate_image_upload(
        filename=filename,
        prefix=prefix,
        content_type=content_type,
        size=size,
    )

    ensure_bucket_exists()
    get_minio_client().put_object(
        minio_settings.bucket,
        metadata.object_key,
        file_obj,
        metadata.size,
        content_type=metadata.content_type,
    )
    return StoredImage(
        object_key=metadata.object_key,
        bucket=minio_settings.bucket,
        content_type=metadata.content_type,
        size=metadata.size,
    )


def upload_fastapi_image(
    upload: UploadFile,
    *,
    prefix: str,
) -> StoredImage:
    filename = upload.filename or "upload.jpg"
    return upload_image_file(
        upload.file,
        filename=filename,
        prefix=prefix,
        content_type=upload.content_type,
    )
