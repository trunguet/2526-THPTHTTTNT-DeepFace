import pytest
from sqlalchemy import create_engine, insert, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.schema import access_logs, employees, face_embeddings, metadata
from app.ml.embedder import FaceEmbeddingResult
from app.services.embedding_service import (
    DuplicateFaceRegistrationError,
    EmployeeNotFoundError,
    create_employee_embedding,
)
from app.services.face_pipeline_service import (
    AccessLogNotFoundError,
    process_access_check,
)
from app.config.settings import settings
from app.services.vector_store_service import VectorSearchCandidate


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    metadata.create_all(engine)
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    db = testing_session_local()
    try:
        yield db
    finally:
        db.close()


def seed_employee(db_session, *, employee_id: int = 1, status: str = "active") -> None:
    db_session.execute(
        insert(employees).values(
            id=employee_id,
            code=f"EMP{employee_id:03d}",
            name=f"Employee {employee_id}",
            department="Security",
            status=status,
        )
    )
    db_session.commit()


def seed_access_log(
    db_session,
    *,
    log_id: int = 1,
    image_path: str = "/app/storage/uploads/snapshot.jpg",
) -> None:
    db_session.execute(
        insert(access_logs).values(
            id=log_id,
            employee_id=None,
            camera_id=1,
            status="processing",
            score=None,
            image_path=image_path,
        )
    )
    db_session.commit()


def get_access_log(db_session, log_id: int):
    return db_session.execute(
        select(access_logs).where(access_logs.c.id == log_id)
    ).first()


@pytest.fixture()
def deepface_embedding_stub(monkeypatch):
    indexed_embeddings = []

    class DetectionResult:
        detected = True
        face_box = {"x": 0, "y": 0, "w": 64, "h": 64}
        face_image = None

    def fake_create_face_embedding(image_path: str) -> FaceEmbeddingResult:
        return FaceEmbeddingResult(
            image_path=image_path,
            vector=[1.0, 0.0, 0.0],
            model_name="Facenet512",
            dimensions=3,
        )

    monkeypatch.setattr(
        "app.services.embedding_service.create_face_embedding",
        fake_create_face_embedding,
    )
    monkeypatch.setattr(
        "app.services.face_pipeline_service.create_face_embedding",
        fake_create_face_embedding,
    )
    monkeypatch.setattr(
        "app.services.embedding_service.require_face",
        lambda image_path, **_kwargs: DetectionResult(),
    )
    monkeypatch.setattr(
        "app.services.face_pipeline_service.require_face",
        lambda image_path, **_kwargs: DetectionResult(),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.upsert_face_embedding",
        lambda **payload: indexed_embeddings.append(payload),
    )
    monkeypatch.setattr(
        "app.services.embedding_service.ensure_embedding_collection",
        lambda vector_size: None,
    )

    def fake_search_face_embeddings(
        *,
        query_vector: list[float],
        model_name: str,
        limit: int = 10,
    ) -> list[VectorSearchCandidate]:
        return [
            VectorSearchCandidate(
                embedding_id=int(payload["embedding_id"]),
                employee_id=int(payload["employee_id"]),
                score=1.0,
                model_name=str(payload["model_name"]),
            )
            for payload in indexed_embeddings
            if payload["model_name"] == model_name
        ][:limit]

    monkeypatch.setattr(
        "app.services.face_pipeline_service.search_face_embeddings",
        fake_search_face_embeddings,
    )
    monkeypatch.setattr(
        "app.services.embedding_service.search_face_embeddings",
        fake_search_face_embeddings,
    )


def test_create_employee_embedding_stores_deepface_embedding(
    db_session,
    deepface_embedding_stub,
):
    seed_employee(db_session)

    stored_embedding = create_employee_embedding(
        db_session,
        employee_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )

    assert stored_embedding.id == 1
    assert stored_embedding.employee_id == 1
    assert stored_embedding.model_name == "Facenet512"
    assert stored_embedding.source_image_key == "/app/storage/uploads/employee_1.jpg"
    assert len(stored_embedding.vector) == 3

    row = db_session.execute(select(face_embeddings)).first()
    assert row is not None
    assert row.employee_id == 1
    assert row.vector == stored_embedding.vector
    assert row.source_image_key == "/app/storage/uploads/employee_1.jpg"


def test_create_employee_embedding_rejects_missing_employee(db_session):
    with pytest.raises(EmployeeNotFoundError):
        create_employee_embedding(
            db_session,
            employee_id=999,
            image_path="/app/storage/uploads/employee_1.jpg",
        )


def test_create_employee_embedding_rejects_duplicate_active_face(
    db_session,
    deepface_embedding_stub,
):
    seed_employee(db_session, employee_id=1)
    create_employee_embedding(
        db_session,
        employee_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )
    seed_employee(db_session, employee_id=2)

    with pytest.raises(DuplicateFaceRegistrationError, match="already registered"):
        create_employee_embedding(
            db_session,
            employee_id=2,
            image_path="/app/storage/uploads/employee_2.jpg",
        )

    rows = db_session.execute(select(face_embeddings)).all()
    assert len(rows) == 1


def test_process_access_check_grants_matching_active_employee(
    db_session,
    deepface_embedding_stub,
):
    seed_employee(db_session)
    create_employee_embedding(
        db_session,
        employee_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )
    seed_access_log(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )

    decision = process_access_check(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )

    assert decision.status == "granted"
    assert decision.employee_id == 1
    assert decision.score == 1.0

    row = get_access_log(db_session, 1)
    assert row.status == "granted"
    assert row.employee_id == 1
    assert row.score == 1.0
    assert row.message == "Face matched embedding from Qdrant."


def test_process_access_check_denies_when_no_embeddings_exist(
    db_session,
    deepface_embedding_stub,
):
    seed_access_log(db_session, log_id=1)

    decision = process_access_check(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/snapshot.jpg",
    )

    assert decision.status == "denied"
    assert decision.employee_id is None
    assert decision.score is None

    row = get_access_log(db_session, 1)
    assert row.status == "denied"
    assert row.employee_id is None
    assert row.score is None
    assert row.message == "No active Qdrant face embeddings available for matching."


def test_process_access_check_marks_log_error_when_pipeline_fails(db_session, monkeypatch):
    def raise_no_face(image_path: str, **_kwargs):
        raise ValueError("No face detected by DeepFace.")

    monkeypatch.setattr(
        "app.services.face_pipeline_service.require_face",
        raise_no_face,
    )
    seed_access_log(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/no_face.jpg",
    )

    decision = process_access_check(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/no_face.jpg",
    )

    assert decision.status == "error"
    assert "No face detected" in decision.message

    row = get_access_log(db_session, 1)
    assert row.status == "error"
    assert row.employee_id is None
    assert row.score is None
    assert "No face detected" in row.message


def test_process_access_check_uses_access_detector_backend(
    db_session,
    deepface_embedding_stub,
    monkeypatch,
):
    detector_backends = []

    class DetectionResult:
        detected = True
        face_image = object()

    monkeypatch.setattr(
        "app.services.face_pipeline_service.require_face",
        lambda image_path, **kwargs: detector_backends.append(
            kwargs.get("detector_backend")
        )
        or DetectionResult(),
    )
    seed_employee(db_session)
    create_employee_embedding(
        db_session,
        employee_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )
    seed_access_log(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )

    process_access_check(
        db_session,
        log_id=1,
        image_path="/app/storage/uploads/employee_1.jpg",
    )

    assert detector_backends == [settings.deepface_access_detector_backend]


def test_process_access_check_raises_for_missing_log(db_session):
    with pytest.raises(AccessLogNotFoundError):
        process_access_check(
            db_session,
            log_id=999,
            image_path="/app/storage/uploads/snapshot.jpg",
        )
