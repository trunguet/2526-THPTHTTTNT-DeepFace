import os
import shutil

import numpy as np

from app.config import ARCFACE_WEIGHTS_PATH


class ArcFaceEmbedder:
    def __init__(self, weights_path: str = ARCFACE_WEIGHTS_PATH, model_name: str = "ArcFace"):
        self.weights_path = weights_path
        self.model_name = model_name
        self._ensure_deepface_weight()
        os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

        try:
            from deepface import DeepFace
        except Exception as exc:  # pragma: no cover - depends on optional ML runtime
            raise RuntimeError(f"deepface is required for ArcFace embeddings: {exc}") from exc

        self._deepface = DeepFace

    def _ensure_deepface_weight(self) -> None:
        if not self.weights_path or not os.path.exists(self.weights_path):
            return

        target_dir = os.path.join(os.path.expanduser("~"), ".deepface", "weights")
        target_path = os.path.join(target_dir, "arcface_weights.h5")
        if os.path.abspath(self.weights_path) == os.path.abspath(target_path):
            return

        os.makedirs(target_dir, exist_ok=True)
        if not os.path.exists(target_path) or os.path.getsize(target_path) != os.path.getsize(self.weights_path):
            shutil.copyfile(self.weights_path, target_path)

    def embed(self, aligned_face_bgr: np.ndarray) -> np.ndarray:
        embedding_objs = self._deepface.represent(
            img_path=aligned_face_bgr,
            model_name=self.model_name,
            detector_backend="skip",
            enforce_detection=False,
        )
        if not embedding_objs:
            raise RuntimeError("ArcFace did not return an embedding")

        embedding = np.asarray(embedding_objs[0]["embedding"], dtype=np.float32)
        norm = float(np.linalg.norm(embedding))
        if norm == 0:
            raise RuntimeError("ArcFace returned a zero embedding")
        return embedding / norm
