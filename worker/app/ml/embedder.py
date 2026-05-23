from dataclasses import dataclass
from typing import Any

from app.config.settings import settings
from app.ml.deepface_client import load_deepface

DEEPFACE_MODEL_NAME = settings.deepface_model_name


@dataclass(frozen=True)
class FaceEmbeddingResult:
    image_path: str
    vector: list[float]
    model_name: str
    dimensions: int


def _extract_embedding_vector(represent_result: Any) -> list[float]:
    if not isinstance(represent_result, list) or not represent_result:
        raise ValueError("DeepFace did not return any face embedding.")

    first_face = represent_result[0]
    if not isinstance(first_face, dict) or "embedding" not in first_face:
        raise ValueError("DeepFace returned an unexpected embedding format.")

    vector = first_face["embedding"]
    if not isinstance(vector, list) or not vector:
        raise ValueError("DeepFace embedding vector is empty.")

    try:
        return [float(value) for value in vector]
    except (TypeError, ValueError) as exc:
        raise ValueError("DeepFace embedding vector contains non-numeric values.") from exc


def create_face_embedding(
    image_path: str,
    *,
    model_name: str = settings.deepface_model_name,
    detector_backend: str = settings.deepface_detector_backend,
    enforce_detection: bool = settings.deepface_enforce_detection,
    align: bool = settings.deepface_align,
    normalization: str = settings.deepface_normalization,
) -> FaceEmbeddingResult:
    normalized_path = image_path.strip()
    if not normalized_path:
        raise ValueError("Image path is empty.")

    represent_result = load_deepface().represent(
        img_path=normalized_path,
        model_name=model_name,
        detector_backend=detector_backend,
        enforce_detection=enforce_detection,
        align=align,
        normalization=normalization,
    )
    vector = _extract_embedding_vector(represent_result)
    return FaceEmbeddingResult(
        image_path=normalized_path,
        vector=vector,
        model_name=model_name,
        dimensions=len(vector),
    )


def create_face_embedding_from_face(
    face_image: Any,
    *,
    source_image_path: str,
    model_name: str = settings.deepface_model_name,
    normalization: str = settings.deepface_normalization,
) -> FaceEmbeddingResult:
    if face_image is None:
        raise ValueError("Face crop is empty.")

    source_path = source_image_path.strip()
    if not source_path:
        raise ValueError("Image path is empty.")

    represent_result = load_deepface().represent(
        img_path=face_image,
        model_name=model_name,
        detector_backend="skip",
        enforce_detection=False,
        align=False,
        normalization=normalization,
    )
    vector = _extract_embedding_vector(represent_result)
    return FaceEmbeddingResult(
        image_path=source_path,
        vector=vector,
        model_name=model_name,
        dimensions=len(vector),
    )
