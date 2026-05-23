import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.access_log import AccessLog
from app.models.camera import Camera
from app.models.user import User


@pytest.fixture()
def client():
    engine = create_engine(
        "sqlite+pysqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    Base.metadata.create_all(bind=engine)

    with testing_session_local() as db:
        db.add(
            User(
                username="admin",
                password_hash=hash_password("admin123"),
                role="admin",
            )
        )
        db.add(
            User(
                username="user",
                password_hash=hash_password("user123"),
                role="user",
            )
        )
        db.add(
            Camera(
                name="Main Gate",
                location="Lobby",
                stream_url=None,
                status="active",
            )
        )
        db.commit()

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def user_headers(client):
    response = client.post(
        "/auth/login",
        json={"username": "user", "password": "user123"},
    )
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_access_check_requires_auth(client):
    response = client.post(
        "/access/check",
        json={
            "camera_id": 1,
            "image_path": "/app/storage/uploads/snapshot.jpg",
        },
    )

    assert response.status_code == 401


def test_access_check_returns_404_for_missing_camera(client, auth_headers):
    response = client.post(
        "/access/check",
        headers=auth_headers,
        json={
            "camera_id": 999,
            "image_path": "/app/storage/uploads/snapshot.jpg",
        },
    )

    assert response.status_code == 404


def test_access_check_queues_job(client, auth_headers, monkeypatch):
    from app.queues.access_queue import AccessJob

    queued_jobs = []

    def fake_enqueue_access_job(
        log_id: int,
        camera_id: int,
        image_path: str,
    ) -> AccessJob:
        queued_jobs.append(
            {
                "log_id": log_id,
                "camera_id": camera_id,
                "image_path": image_path,
            }
        )
        return AccessJob(
            job_id="access-job-123",
            type="access_check",
            log_id=log_id,
            camera_id=camera_id,
            image_path=image_path,
        )

    monkeypatch.setattr(
        "app.services.access_service.enqueue_access_job",
        fake_enqueue_access_job,
    )

    response = client.post(
        "/access/check",
        headers=auth_headers,
        json={
            "camera_id": 1,
            "image_path": "/app/storage/uploads/snapshot.jpg",
        },
    )

    assert response.status_code == 202
    body = response.json()
    assert body["log_id"]
    assert body["job_id"] == "access-job-123"
    assert body["status"] == "processing"
    assert body["employee_id"] is None
    assert body["camera_id"] == 1
    assert body["score"] is None
    assert body["image_path"] == "/app/storage/uploads/snapshot.jpg"
    assert body["created_at"]

    logs_response = client.get("/logs", headers=auth_headers)
    assert logs_response.status_code == 200
    logs_body = logs_response.json()
    assert len(logs_body) == 1
    assert logs_body[0]["id"] == body["log_id"]
    assert logs_body[0]["status"] == "processing"
    assert queued_jobs == [
        {
            "log_id": body["log_id"],
            "camera_id": 1,
            "image_path": "/app/storage/uploads/snapshot.jpg",
        }
    ]


def test_access_check_image_uploads_and_queues_job(client, auth_headers, monkeypatch):
    from app.queues.access_queue import AccessJob
    from app.services.storage_service import StoredImage

    queued_jobs = []

    def fake_upload_fastapi_image(upload, *, prefix: str) -> StoredImage:
        assert prefix == "access-snapshots"
        return StoredImage(
            object_key="access-snapshots/snapshot.jpg",
            bucket="deepface-images",
            content_type="image/jpeg",
            size=3,
        )

    def fake_enqueue_access_job(
        log_id: int,
        camera_id: int,
        image_key: str,
    ) -> AccessJob:
        queued_jobs.append(
            {
                "log_id": log_id,
                "camera_id": camera_id,
                "image_key": image_key,
            }
        )
        return AccessJob(
            job_id="access-job-image-123",
            type="access_check",
            log_id=log_id,
            camera_id=camera_id,
            image_path=image_key,
            image_key=image_key,
        )

    monkeypatch.setattr(
        "app.api.access.upload_fastapi_image",
        fake_upload_fastapi_image,
    )
    monkeypatch.setattr(
        "app.services.access_service.enqueue_access_job",
        fake_enqueue_access_job,
    )

    response = client.post(
        "/access/check-image",
        headers=auth_headers,
        data={"camera_id": "1"},
        files={"file": ("snapshot.jpg", b"abc", "image/jpeg")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "access-job-image-123"
    assert body["status"] == "processing"
    assert body["image_key"] == "access-snapshots/snapshot.jpg"
    assert body["image_path"] == "access-snapshots/snapshot.jpg"
    assert queued_jobs == [
        {
            "log_id": body["log_id"],
            "camera_id": 1,
            "image_key": "access-snapshots/snapshot.jpg",
        }
    ]


def test_user_role_can_check_access_image(client, user_headers, monkeypatch):
    from app.queues.access_queue import AccessJob
    from app.services.storage_service import StoredImage

    def fake_upload_fastapi_image(upload, *, prefix: str) -> StoredImage:
        return StoredImage(
            object_key="access-snapshots/user-snapshot.jpg",
            bucket="deepface-images",
            content_type="image/jpeg",
            size=3,
        )

    def fake_enqueue_access_job(
        log_id: int,
        camera_id: int,
        image_key: str,
    ) -> AccessJob:
        return AccessJob(
            job_id="user-access-job-123",
            type="access_check",
            log_id=log_id,
            camera_id=camera_id,
            image_path=image_key,
            image_key=image_key,
        )

    monkeypatch.setattr(
        "app.api.access.upload_fastapi_image",
        fake_upload_fastapi_image,
    )
    monkeypatch.setattr(
        "app.services.access_service.enqueue_access_job",
        fake_enqueue_access_job,
    )

    response = client.post(
        "/access/check-image",
        headers=user_headers,
        data={"camera_id": "1"},
        files={"file": ("snapshot.jpg", b"abc", "image/jpeg")},
    )

    assert response.status_code == 202
    assert response.json()["job_id"] == "user-access-job-123"


def test_access_check_returns_429_when_processing_queue_is_full(client, auth_headers):
    db = next(app.dependency_overrides[get_db]())
    try:
        db.add_all(
            [
                AccessLog(
                    camera_id=1,
                    status="processing",
                    image_path="access-snapshots/pending-1.jpg",
                    message="pending",
                ),
                AccessLog(
                    camera_id=1,
                    status="processing",
                    image_path="access-snapshots/pending-2.jpg",
                    message="pending",
                ),
                AccessLog(
                    camera_id=1,
                    status="processing",
                    image_path="access-snapshots/pending-3.jpg",
                    message="pending",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()

    response = client.post(
        "/access/check",
        headers=auth_headers,
        json={
            "camera_id": 1,
            "image_path": "/app/storage/uploads/snapshot.jpg",
        },
    )

    assert response.status_code == 429
    assert "too many frames waiting to be processed" in response.json()["detail"]
