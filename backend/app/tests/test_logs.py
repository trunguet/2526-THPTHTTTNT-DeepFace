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
        user = User(
            username="admin",
            password_hash=hash_password("admin123"),
            role="admin",
        )
        employee = Employee(
            code="EMP001",
            name="Nguyen Van A",
            department="Security",
            status="active",
        )
        camera = Camera(
            name="Main Gate",
            location="Lobby",
            stream_url=None,
            status="active",
        )
        db.add_all([user, employee, camera])
        db.flush()
        db.add(
            AccessLog(
                employee_id=employee.id,
                camera_id=camera.id,
                status="granted",
                score=0.91,
                image_path="/app/storage/uploads/snapshot.jpg",
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


def test_list_logs_requires_auth(client):
    response = client.get("/logs")

    assert response.status_code == 401


def test_list_logs(client, auth_headers):
    response = client.get("/logs", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["employee_id"] == 1
    assert body[0]["employee_name"] == "Nguyen Van A"
    assert body[0]["camera_id"] == 1
    assert body[0]["status"] == "granted"
    assert body[0]["score"] == 0.91
    assert body[0]["image_path"] == "/app/storage/uploads/snapshot.jpg"
    assert body[0]["message"] is None
    assert body[0]["created_at"]
