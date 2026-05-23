from dataclasses import dataclass
from os import getenv


def _get_bool(name: str, default: bool) -> bool:
    value = getenv(name)
    if value is None:
        return default

    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    value = getenv(name)
    if value is None:
        return default

    return float(value)


def _get_int(name: str, default: int) -> int:
    value = getenv(name)
    if value is None:
        return default

    return int(value)


@dataclass(frozen=True)
class Settings:
    app_env: str = getenv("APP_ENV", "dev")
    redis_url: str = getenv("REDIS_URL", "redis://localhost:6379/0")
    database_url: str = getenv(
        "DATABASE_URL",
        "postgresql://deepface:deepface@localhost:5432/deepface_access",
    )
    deepface_model_name: str = getenv("DEEPFACE_MODEL_NAME", "Facenet512")
    deepface_detector_backend: str = getenv("DEEPFACE_DETECTOR_BACKEND", "mtcnn")
    deepface_access_detector_backend: str = getenv(
        "DEEPFACE_ACCESS_DETECTOR_BACKEND",
        getenv("DEEPFACE_DETECTOR_BACKEND", "mtcnn"),
    )
    deepface_face_count_backend: str = getenv("DEEPFACE_FACE_COUNT_BACKEND", "")
    deepface_enforce_detection: bool = _get_bool("DEEPFACE_ENFORCE_DETECTION", True)
    deepface_align: bool = _get_bool("DEEPFACE_ALIGN", False)
    deepface_normalization: str = getenv("DEEPFACE_NORMALIZATION", "base")
    deepface_match_threshold: float = _get_float("DEEPFACE_MATCH_THRESHOLD", 0.70)
    deepface_duplicate_threshold: float = _get_float(
        "DEEPFACE_DUPLICATE_THRESHOLD",
        0.95,
    )
    deepface_warmup_on_start: bool = _get_bool("DEEPFACE_WARMUP_ON_START", True)


settings = Settings()
