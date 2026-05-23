from dataclasses import dataclass
from pathlib import PurePath
from uuid import uuid4


SUPPORTED_IMAGE_CONTENT_TYPES = {
    "image/bmp",
    "image/jpeg",
    "image/png",
    "image/webp",
}
SUPPORTED_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}
MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024


class ImageValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ImageUploadMetadata:
    object_key: str
    content_type: str
    size: int


def validate_image_extension(filename: str) -> str:
    extension = PurePath(filename).suffix.lower()
    if extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ImageValidationError(f"Unsupported image extension: {extension or '<none>'}")

    return extension


def validate_image_content_type(content_type: str | None) -> str:
    resolved_content_type = (content_type or "application/octet-stream").lower()
    if resolved_content_type not in SUPPORTED_IMAGE_CONTENT_TYPES:
        raise ImageValidationError(
            f"Unsupported image content type: {resolved_content_type}"
        )

    return resolved_content_type


def validate_image_size(size: int) -> None:
    if size <= 0:
        raise ImageValidationError("Uploaded image is empty.")

    if size > MAX_IMAGE_SIZE_BYTES:
        max_mb = MAX_IMAGE_SIZE_BYTES // (1024 * 1024)
        raise ImageValidationError(f"Uploaded image is too large. Max size is {max_mb} MB.")


def build_image_object_key(prefix: str, filename: str) -> str:
    extension = validate_image_extension(filename)
    normalized_prefix = prefix.strip("/").replace("\\", "/")
    return f"{normalized_prefix}/{uuid4().hex}{extension}"


def validate_image_upload(
    *,
    filename: str,
    prefix: str,
    content_type: str | None,
    size: int,
) -> ImageUploadMetadata:
    validate_image_size(size)
    resolved_content_type = validate_image_content_type(content_type)
    object_key = build_image_object_key(prefix, filename)
    return ImageUploadMetadata(
        object_key=object_key,
        content_type=resolved_content_type,
        size=size,
    )
