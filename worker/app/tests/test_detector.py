import pytest

from app.ml import detector
from app.ml.detector import detect_face, require_face


class FakeDeepFace:
    calls = []

    @staticmethod
    def extract_faces(**kwargs):
        FakeDeepFace.calls.append(kwargs)
        return [
            {
                "facial_area": {"x": 10, "y": 20, "w": 120, "h": 140},
                "face_confidence": 0.97,
            }
        ]


def test_detect_face_uses_deepface_extract_faces(monkeypatch):
    FakeDeepFace.calls = []
    monkeypatch.setattr(detector, "load_deepface", lambda: FakeDeepFace)

    result = detect_face("/app/storage/uploads/employee_1.jpg")

    assert result.detected is True
    assert result.image_path == "/app/storage/uploads/employee_1.jpg"
    assert result.face_box is not None
    assert result.face_box.x == 10
    assert result.face_box.y == 20
    assert result.face_box.width == 120
    assert result.face_box.height == 140
    assert result.confidence == 0.97
    assert result.face_count == 1
    assert result.message == "Face detected by DeepFace."
    assert FakeDeepFace.calls == [
            {
                "img_path": "/app/storage/uploads/employee_1.jpg",
                "detector_backend": "mtcnn",
                "enforce_detection": True,
                "align": False,
        }
    ]


def test_detect_face_accepts_custom_options(monkeypatch):
    FakeDeepFace.calls = []
    monkeypatch.setattr(detector, "load_deepface", lambda: FakeDeepFace)

    result = detect_face(
        "/app/storage/uploads/employee_1.jpg",
        detector_backend="retinaface",
        enforce_detection=False,
        align=False,
    )

    assert result.detected is True
    assert FakeDeepFace.calls[0]["detector_backend"] == "retinaface"
    assert FakeDeepFace.calls[0]["enforce_detection"] is False
    assert FakeDeepFace.calls[0]["align"] is False


def test_detect_face_rejects_empty_image_path():
    result = detect_face("")

    assert result.detected is False
    assert result.face_box is None
    assert result.confidence == 0.0
    assert result.message == "Image path is empty."


def test_detect_face_rejects_unsupported_extension():
    result = detect_face("/app/storage/uploads/not_an_image.txt")

    assert result.detected is False
    assert result.face_box is None
    assert result.confidence == 0.0
    assert "Unsupported image extension" in result.message


def test_detect_face_returns_not_detected_when_deepface_fails(monkeypatch):
    class NoFaceDeepFace:
        @staticmethod
        def extract_faces(**kwargs):
            raise ValueError("No face detected by DeepFace.")

    monkeypatch.setattr(detector, "load_deepface", lambda: NoFaceDeepFace)

    result = detect_face("/app/storage/uploads/no_face.jpg")

    assert result.detected is False
    assert result.face_box is None
    assert result.confidence == 0.0
    assert result.message == "No face detected by DeepFace."


def test_detect_face_rejects_unexpected_deepface_format(monkeypatch):
    class BadDeepFace:
        @staticmethod
        def extract_faces(**kwargs):
            return [{"not_facial_area": {}}]

    monkeypatch.setattr(detector, "load_deepface", lambda: BadDeepFace)

    result = detect_face("/app/storage/uploads/employee_1.jpg")

    assert result.detected is False
    assert "facial area" in result.message


def test_detect_face_rejects_multiple_faces(monkeypatch):
    class MultipleFacesDeepFace:
        @staticmethod
        def extract_faces(**kwargs):
            return [
                {
                    "facial_area": {"x": 10, "y": 20, "w": 120, "h": 140},
                    "face_confidence": 0.97,
                },
                {
                    "facial_area": {"x": 150, "y": 20, "w": 110, "h": 130},
                    "face_confidence": 0.96,
                },
            ]

    monkeypatch.setattr(detector, "load_deepface", lambda: MultipleFacesDeepFace)

    result = detect_face(
        "/app/storage/uploads/two_faces.jpg",
        face_count_backend="retinaface",
    )

    assert result.detected is False
    assert result.face_count == 2
    assert "Multiple faces detected" in result.message


def test_detect_face_rejects_when_count_backend_finds_multiple_faces(monkeypatch):
    class CountBackendDeepFace:
        calls = []

        @staticmethod
        def extract_faces(**kwargs):
            CountBackendDeepFace.calls.append(kwargs)
            if kwargs["detector_backend"] == "retinaface":
                return [
                    {
                        "facial_area": {"x": 10, "y": 20, "w": 120, "h": 140},
                        "face_confidence": 0.97,
                    },
                    {
                        "facial_area": {"x": 150, "y": 20, "w": 110, "h": 130},
                        "face_confidence": 0.96,
                    },
                ]

            return [
                {
                    "facial_area": {"x": 10, "y": 20, "w": 120, "h": 140},
                    "face_confidence": 0.97,
                }
            ]

    monkeypatch.setattr(detector, "load_deepface", lambda: CountBackendDeepFace)

    result = detect_face(
        "/app/storage/uploads/two_faces.jpg",
        face_count_backend="retinaface",
    )

    assert result.detected is False
    assert result.face_count == 2
    assert "Frame rejected" in result.message
    assert [call["detector_backend"] for call in CountBackendDeepFace.calls] == [
        "retinaface"
    ]


def test_require_face_returns_detection_for_supported_image_path(monkeypatch):
    monkeypatch.setattr(detector, "load_deepface", lambda: FakeDeepFace)

    result = require_face("/app/storage/uploads/employee_1.jpg")

    assert result.detected is True
    assert result.face_box is not None


def test_require_face_raises_when_face_is_not_detected(monkeypatch):
    class NoFaceDeepFace:
        @staticmethod
        def extract_faces(**kwargs):
            raise ValueError("No face detected by DeepFace.")

    monkeypatch.setattr(detector, "load_deepface", lambda: NoFaceDeepFace)

    with pytest.raises(ValueError, match="No face detected"):
        require_face("/app/storage/uploads/no_face.jpg")
