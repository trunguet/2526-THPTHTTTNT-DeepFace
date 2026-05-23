from dataclasses import dataclass
from contextlib import contextmanager
from pathlib import Path
from tempfile import NamedTemporaryFile
from collections.abc import Iterator

from app.config.minio import get_minio_client, minio_settings

SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


@dataclass(frozen=True)
class ResolvedImagePath:
    original_path: str
    normalized_path: str
    exists: bool


def resolve_image_path(image_path: str) -> ResolvedImagePath:
    normalized_path = image_path.strip()
    if not normalized_path:
        raise ValueError("Image path is empty.")

    extension = Path(normalized_path).suffix.lower()
    if extension and extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {extension}")

    return ResolvedImagePath(
        original_path=image_path,
        normalized_path=normalized_path,
        exists=Path(normalized_path).is_file(),
    )


def is_object_key(image_reference: str) -> bool:
    normalized_reference = image_reference.strip()
    if not normalized_reference:
        raise ValueError("Image path is empty.")

    if normalized_reference.startswith(("/", "\\")):
        return False

    if len(normalized_reference) > 2 and normalized_reference[1] == ":":
        return False

    path = Path(normalized_reference)
    return not path.is_file()


def download_image_object(object_key: str) -> Path:
    extension = Path(object_key).suffix.lower()
    if extension and extension not in SUPPORTED_IMAGE_EXTENSIONS:
        raise ValueError(f"Unsupported image extension: {extension}")

    response = get_minio_client().get_object(minio_settings.bucket, object_key)
    with NamedTemporaryFile(delete=False, suffix=extension or ".jpg") as temp_file:
        try:
            for chunk in response.stream(32 * 1024):
                temp_file.write(chunk)
        finally:
            response.close()
            response.release_conn()

        return Path(temp_file.name)


@contextmanager
def resolved_image_file(image_reference: str) -> Iterator[ResolvedImagePath]:
    if is_object_key(image_reference):
        temp_path = download_image_object(image_reference.strip())
        try:
            yield ResolvedImagePath(
                original_path=image_reference,
                normalized_path=str(temp_path),
                exists=True,
            )
        finally:
            temp_path.unlink(missing_ok=True)
        return

    yield resolve_image_path(image_reference)
