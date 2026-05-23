from typing import Any


def load_deepface() -> Any:
    try:
        from deepface import DeepFace
    except ImportError as exc:
        raise RuntimeError(
            "DeepFace is not installed. Install worker requirements or rebuild the worker image."
        ) from exc

    return DeepFace


def warm_up_deepface_model(*, model_name: str, normalization: str) -> None:
    import numpy as np

    load_deepface().represent(
        img_path=np.zeros((160, 160, 3), dtype=np.uint8),
        model_name=model_name,
        detector_backend="skip",
        enforce_detection=False,
        align=False,
        normalization=normalization,
    )
