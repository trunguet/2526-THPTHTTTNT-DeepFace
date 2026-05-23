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
from app.models.employee import Employee
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
            Employee(
                code="EMP001",
                name="Nguyen Van A",
                department="Security",
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


def test_list_employees_requires_auth(client):
    response = client.get("/employees")

    assert response.status_code == 401


def test_list_employees(client, auth_headers):
    response = client.get("/employees", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["code"] == "EMP001"
    assert body[0]["embedding_status"] == "none"
    assert body[0]["embedding_error"] is None


def test_create_employee(client, auth_headers):
    response = client.post(
        "/employees",
        headers=auth_headers,
        json={
            "code": "EMP002",
            "name": "Tran Thi B",
            "department": "Operations",
            "status": "active",
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["code"] == "EMP002"
    assert body["name"] == "Tran Thi B"
    assert body["embedding_status"] == "none"


def test_user_role_cannot_create_employee(client, user_headers):
    response = client.post(
        "/employees",
        headers=user_headers,
        json={
            "code": "EMP002",
            "name": "Tran Thi B",
            "department": "Operations",
            "status": "active",
        },
    )

    assert response.status_code == 403


def test_create_employee_rejects_duplicate_code(client, auth_headers):
    response = client.post(
        "/employees",
        headers=auth_headers,
        json={
            "code": "EMP001",
            "name": "Duplicate",
            "department": None,
            "status": "active",
        },
    )

    assert response.status_code == 409


def test_get_employee_by_id(client, auth_headers):
    response = client.get("/employees/1", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["code"] == "EMP001"


def test_get_employee_by_id_returns_404(client, auth_headers):
    response = client.get("/employees/999", headers=auth_headers)

    assert response.status_code == 404


def test_update_employee(client, auth_headers):
    response = client.put(
        "/employees/1",
        headers=auth_headers,
        json={
            "name": "Nguyen Van A Updated",
            "department": "Admin",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["code"] == "EMP001"
    assert body["name"] == "Nguyen Van A Updated"
    assert body["department"] == "Admin"


def test_delete_employee_soft_deletes_record(client, auth_headers):
    delete_response = client.delete("/employees/1", headers=auth_headers)

    assert delete_response.status_code == 204

    get_response = client.get("/employees/1", headers=auth_headers)
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "inactive"


def test_create_embedding_job_requires_auth(client):
    response = client.post(
        "/employees/1/embedding-jobs",
        json={"image_path": "/app/storage/uploads/employee_1.jpg"},
    )

    assert response.status_code == 401


def test_create_embedding_job_returns_404_for_missing_employee(
    client,
    auth_headers,
):
    response = client.post(
        "/employees/999/embedding-jobs",
        headers=auth_headers,
        json={"image_path": "/app/storage/uploads/employee_999.jpg"},
    )

    assert response.status_code == 404


def test_create_embedding_job_queues_job(client, auth_headers, monkeypatch):
    from app.queues.embedding_queue import EmbeddingJob

    queued_jobs = []

    def fake_enqueue_embedding_job(employee_id: int, image_path: str) -> EmbeddingJob:
        queued_jobs.append({"employee_id": employee_id, "image_path": image_path})
        return EmbeddingJob(
            job_id="job-123",
            type="embedding",
            employee_id=employee_id,
            image_path=image_path,
        )

    monkeypatch.setattr(
        "app.services.employee_service.enqueue_embedding_job",
        fake_enqueue_embedding_job,
    )

    response = client.post(
        "/employees/1/embedding-jobs",
        headers=auth_headers,
        json={"image_path": "/app/storage/uploads/employee_1.jpg"},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["job_id"] == "job-123"
    assert body["type"] == "embedding"
    assert body["employee_id"] == 1
    assert body["image_path"] == "/app/storage/uploads/employee_1.jpg"
    assert body["queue_name"] == "embedding_jobs"
    employee_response = client.get("/employees/1", headers=auth_headers)
    assert employee_response.json()["embedding_status"] == "pending"
    assert employee_response.json()["embedding_error"] is None
    assert queued_jobs == [
        {
            "employee_id": 1,
            "image_path": "/app/storage/uploads/employee_1.jpg",
        }
    ]


def test_upload_employee_face_image_uploads_and_queues_embedding(
    client,
    auth_headers,
    monkeypatch,
):
    from app.queues.embedding_queue import EmbeddingJob
    from app.services.storage_service import StoredImage

    queued_jobs = []

    def fake_upload_fastapi_image(upload, *, prefix: str) -> StoredImage:
        assert prefix == "employee-faces/1"
        return StoredImage(
            object_key="employee-faces/1/reference.jpg",
            bucket="deepface-images",
            content_type="image/jpeg",
            size=3,
        )

    def fake_enqueue_embedding_job(employee_id: int, image_key: str) -> EmbeddingJob:
        queued_jobs.append({"employee_id": employee_id, "image_key": image_key})
        return EmbeddingJob(
            job_id="embedding-image-123",
            type="embedding",
            employee_id=employee_id,
            image_path=image_key,
            image_key=image_key,
        )

    monkeypatch.setattr(
        "app.api.employees.upload_fastapi_image",
        fake_upload_fastapi_image,
    )
    monkeypatch.setattr(
        "app.services.employee_service.enqueue_embedding_job",
        fake_enqueue_embedding_job,
    )

    response = client.post(
        "/employees/1/face-image",
        headers=auth_headers,
        files={"file": ("reference.jpg", b"abc", "image/jpeg")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["object_key"] == "employee-faces/1/reference.jpg"
    assert body["job_id"] == "embedding-image-123"
    assert body["queue_name"] == "embedding_jobs"
    employee_response = client.get("/employees/1", headers=auth_headers)
    assert employee_response.json()["embedding_status"] == "pending"
    assert employee_response.json()["embedding_error"] is None
    assert queued_jobs == [
        {
            "employee_id": 1,
            "image_key": "employee-faces/1/reference.jpg",
        }
    ]
