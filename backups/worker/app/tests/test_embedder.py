import pytest

from app.ml import embedder
from app.ml.embedder import create_face_embedding, create_face_embedding_from_face


class FakeDeepFace:
    calls = []

    @staticmethod
    def represent(**kwargs):
        FakeDeepFace.calls.append(kwargs)
        return [
            {
                "embedding": [0.1, 0.2, 0.3],
                "facial_area": {"x": 1, "y": 2, "w": 10, "h": 10},
            }
        ]


def test_create_face_embedding_calls_deepface_represent(monkeypatch):
    FakeDeepFace.calls = []
    monkeypatch.setattr(embedder, "load_deepface", lambda: FakeDeepFace)

    result = create_face_embedding("/app/storage/uploads/employee_1.jpg")

    assert result.image_path == "/app/storage/uploads/employee_1.jpg"
    assert result.model_name == "Facenet512"
    assert result.dimensions == 3
    assert result.vector == [0.1, 0.2, 0.3]
    assert FakeDeepFace.calls == [
        {
            "img_path": "/app/storage/uploads/employee_1.jpg",
            "model_name": "Facenet512",
            "detector_backend": "mtcnn",
            "enforce_detection": True,
            "align": False,
            "normalization": "base",
        }
    ]


def test_create_face_embedding_from_face_skips_second_detection(monkeypatch):
    FakeDeepFace.calls = []
    monkeypatch.setattr(embedder, "load_deepface", lambda: FakeDeepFace)

    result = create_face_embedding_from_face(
        object(),
        source_image_path="/tmp/cropped-source.jpg",
    )

    assert result.image_path == "/tmp/cropped-source.jpg"
    assert result.vector == [0.1, 0.2, 0.3]
    assert FakeDeepFace.calls == [
        {
            "img_path": FakeDeepFace.calls[0]["img_path"],
            "model_name": "Facenet512",
            "detector_backend": "skip",
            "enforce_detection": False,
            "align": False,
            "normalization": "base",
        }
    ]


def test_create_face_embedding_accepts_model_options(monkeypatch):
    FakeDeepFace.calls = []
    monkeypatch.setattr(embedder, "load_deepface", lambda: FakeDeepFace)

    result = create_face_embedding(
        "/app/storage/uploads/employee_1.jpg",
        model_name="ArcFace",
        detector_backend="retinaface",
        enforce_detection=False,
        align=False,
        normalization="ArcFace",
    )

    assert result.model_name == "ArcFace"
    assert FakeDeepFace.calls[0]["detector_backend"] == "retinaface"
    assert FakeDeepFace.calls[0]["enforce_detection"] is False
    assert FakeDeepFace.calls[0]["align"] is False
    assert FakeDeepFace.calls[0]["normalization"] == "ArcFace"


def test_create_face_embedding_rejects_empty_image_path():
    with pytest.raises(ValueError, match="Image path is empty"):
        create_face_embedding("")


def test_create_face_embedding_rejects_empty_deepface_result(monkeypatch):
    class EmptyDeepFace:
        @staticmethod
        def represent(**kwargs):
            return []

    monkeypatch.setattr(embedder, "load_deepface", lambda: EmptyDeepFace)

    with pytest.raises(ValueError, match="did not return any face embedding"):
        create_face_embedding("/app/storage/uploads/employee_1.jpg")


def test_create_face_embedding_rejects_unexpected_deepface_format(monkeypatch):
    class BadDeepFace:
        @staticmethod
        def represent(**kwargs):
            return [{"not_embedding": [0.1]}]

    monkeypatch.setattr(embedder, "load_deepface", lambda: BadDeepFace)

    with pytest.raises(ValueError, match="unexpected embedding format"):
        create_face_embedding("/app/storage/uploads/employee_1.jpg")


def test_create_face_embedding_reports_missing_dependency(monkeypatch):
    def raise_import_error():
        raise RuntimeError("DeepFace is not installed.")

    monkeypatch.setattr(embedder, "load_deepface", raise_import_error)

    with pytest.raises(RuntimeError, match="DeepFace is not installed"):
        create_face_embedding("/app/storage/uploads/employee_1.jpg")
