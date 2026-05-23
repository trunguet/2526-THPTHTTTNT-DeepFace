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
                stream_url="rtsp://example.local/main",
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


def test_list_cameras_requires_auth(client):
    response = client.get("/cameras")

    assert response.status_code == 401


def test_list_cameras(client, auth_headers):
    response = client.get("/cameras", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Main Gate"
    assert body[0]["location"] == "Lobby"


def test_create_camera(client, auth_headers):
    response = client.post(
        "/cameras",
        headers=auth_headers,
        json={
            "name": "Back Door",
            "location": "Warehouse",
            "stream_url": "rtsp://example.local/back",
            "status": "active",
        },
    )

    assert response.status_code == 405
    body = response.json()
    assert "read-only" in body["detail"]


def test_user_role_cannot_create_camera(client, user_headers):
    response = client.post(
        "/cameras",
        headers=user_headers,
        json={
            "name": "Back Door",
            "location": "Warehouse",
            "stream_url": "rtsp://example.local/back",
            "status": "active",
        },
    )

    assert response.status_code == 403


def test_get_camera_by_id(client, auth_headers):
    response = client.get("/cameras/1", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Main Gate"
    assert body["status"] == "active"


def test_get_camera_by_id_returns_404(client, auth_headers):
    response = client.get("/cameras/999", headers=auth_headers)

    assert response.status_code == 404


def test_update_camera(client, auth_headers):
    response = client.put(
        "/cameras/1",
        headers=auth_headers,
        json={
            "name": "Main Gate Updated",
            "location": "Front Lobby",
            "stream_url": None,
            "status": "inactive",
        },
    )

    assert response.status_code == 405
    body = response.json()
    assert "read-only" in body["detail"]


def test_update_camera_returns_404(client, auth_headers):
    response = client.put(
        "/cameras/999",
        headers=auth_headers,
        json={"name": "Missing"},
    )

    assert response.status_code == 405


def test_delete_camera_is_not_allowed(client, auth_headers):
    delete_response = client.delete("/cameras/1", headers=auth_headers)

    assert delete_response.status_code == 405
    assert "read-only" in delete_response.json()["detail"]


def test_delete_camera_returns_404(client, auth_headers):
    response = client.delete("/cameras/999", headers=auth_headers)

    assert response.status_code == 405


def test_user_role_cannot_update_or_delete_camera(client, user_headers):
    update_response = client.put(
        "/cameras/1",
        headers=user_headers,
        json={"name": "Blocked"},
    )
    delete_response = client.delete("/cameras/1", headers=user_headers)

    assert update_response.status_code == 403
    assert delete_response.status_code == 403
