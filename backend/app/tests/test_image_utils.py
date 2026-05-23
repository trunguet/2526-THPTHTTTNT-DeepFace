import pytest

from app.utils.image_utils import (
    MAX_IMAGE_SIZE_BYTES,
    ImageValidationError,
    validate_image_upload,
)


def test_validate_image_upload_returns_storage_metadata():
    metadata = validate_image_upload(
        filename="face.JPG",
        prefix="employee-faces/1",
        content_type="image/jpeg",
        size=1024,
    )

    assert metadata.object_key.startswith("employee-faces/1/")
    assert metadata.object_key.endswith(".jpg")
    assert metadata.content_type == "image/jpeg"
    assert metadata.size == 1024


def test_validate_image_upload_rejects_unsupported_extension():
    with pytest.raises(ImageValidationError, match="Unsupported image extension"):
        validate_image_upload(
            filename="face.txt",
            prefix="employee-faces/1",
            content_type="image/jpeg",
            size=1024,
        )


def test_validate_image_upload_rejects_unsupported_content_type():
    with pytest.raises(ImageValidationError, match="Unsupported image content type"):
        validate_image_upload(
            filename="face.jpg",
            prefix="employee-faces/1",
            content_type="text/plain",
            size=1024,
        )


def test_validate_image_upload_rejects_empty_file():
    with pytest.raises(ImageValidationError, match="empty"):
        validate_image_upload(
            filename="face.jpg",
            prefix="employee-faces/1",
            content_type="image/jpeg",
            size=0,
        )


def test_validate_image_upload_rejects_oversized_file():
    with pytest.raises(ImageValidationError, match="too large"):
        validate_image_upload(
            filename="face.jpg",
            prefix="employee-faces/1",
            content_type="image/jpeg",
            size=MAX_IMAGE_SIZE_BYTES + 1,
        )
