from dataclasses import dataclass
from pathlib import PurePath
from typing import Any

from app.config.settings import settings
from app.ml.deepface_client import load_deepface


SUPPORTED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
MULTIPLE_FACE_REJECTION_MESSAGE = (
    "Multiple faces detected. Frame rejected. "
    "Please keep exactly one face in the camera frame."
)


@dataclass(frozen=True)
class FaceBox:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class FaceDetectionResult:
    detected: bool
    image_path: str
    face_box: FaceBox | None
    confidence: float
    message: str
    face_count: int = 0
    face_image: Any | None = None


def _extract_face_count(extract_faces_result: Any) -> int:
    if not isinstance(extract_faces_result, list) or not extract_faces_result:
        raise ValueError("No face detected by DeepFace.")

    return len(extract_faces_result)


def _extract_single_face_area(extract_faces_result: Any) -> tuple[FaceBox, float, int, Any | None]:
    face_count = _extract_face_count(extract_faces_result)
    if face_count > 1:
        raise ValueError(MULTIPLE_FACE_REJECTION_MESSAGE)

    first_face = extract_faces_result[0]
    if not isinstance(first_face, dict):
        raise ValueError("DeepFace returned an unexpected face detection format.")

    facial_area = first_face.get("facial_area")
    if not isinstance(facial_area, dict):
        raise ValueError("DeepFace result does not include facial area.")

    try:
        face_box = FaceBox(
            x=int(facial_area["x"]),
            y=int(facial_area["y"]),
            width=int(facial_area["w"]),
            height=int(facial_area["h"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("DeepFace facial area is incomplete.") from exc

    confidence = first_face.get("face_confidence", first_face.get("confidence", 0.0))
    return face_box, float(confidence or 0.0), face_count, first_face.get("face")


def detect_face(
    image_path: str,
    *,
    detector_backend: str = settings.deepface_detector_backend,
    face_count_backend: str = settings.deepface_face_count_backend,
    enforce_detection: bool = settings.deepface_enforce_detection,
    align: bool = settings.deepface_align,
) -> FaceDetectionResult:
    normalized_path = image_path.strip()
    if not normalized_path:
        return FaceDetectionResult(
            detected=False,
            image_path=image_path,
            face_box=None,
            confidence=0.0,
            message="Image path is empty.",
        )

    extension = PurePath(normalized_path).suffix.lower()
    if extension and extension not in SUPPORTED_IMAGE_EXTENSIONS:
        return FaceDetectionResult(
            detected=False,
            image_path=normalized_path,
            face_box=None,
            confidence=0.0,
            message=f"Unsupported image extension: {extension}",
        )

    try:
        count_faces = None
        if face_count_backend and face_count_backend != detector_backend:
            count_faces = load_deepface().extract_faces(
                img_path=normalized_path,
                detector_backend=face_count_backend,
                enforce_detection=False,
                align=align,
            )
            count = _extract_face_count(count_faces)
            if count > 1:
                return FaceDetectionResult(
                    detected=False,
                    image_path=normalized_path,
                    face_box=None,
                    confidence=0.0,
                    message=MULTIPLE_FACE_REJECTION_MESSAGE,
                    face_count=count,
                )

        faces = load_deepface().extract_faces(
            img_path=normalized_path,
            detector_backend=detector_backend,
            enforce_detection=enforce_detection,
            align=align,
        )
        face_box, confidence, face_count, face_image = _extract_single_face_area(faces)
    except Exception as exc:
        return FaceDetectionResult(
            detected=False,
            image_path=normalized_path,
            face_box=None,
            confidence=0.0,
            message=str(exc),
            face_count=(
                len(faces)
                if isinstance(locals().get("faces"), list)
                else len(count_faces)
                if isinstance(locals().get("count_faces"), list)
                else 0
            ),
        )

    return FaceDetectionResult(
        detected=True,
        image_path=normalized_path,
        face_box=face_box,
        confidence=confidence,
        message="Face detected by DeepFace.",
        face_count=face_count,
        face_image=face_image,
    )


def require_face(
    image_path: str,
    *,
    detector_backend: str = settings.deepface_detector_backend,
    face_count_backend: str = settings.deepface_face_count_backend,
    enforce_detection: bool = settings.deepface_enforce_detection,
    align: bool = settings.deepface_align,
) -> FaceDetectionResult:
    result = detect_face(
        image_path,
        detector_backend=detector_backend,
        face_count_backend=face_count_backend,
        enforce_detection=enforce_detection,
        align=align,
    )
    if not result.detected:
        raise ValueError(result.message)

    return result
