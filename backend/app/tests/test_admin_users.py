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
        db.add_all(
            [
                User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    role="admin",
                ),
                User(
                    username="user",
                    password_hash=hash_password("user123"),
                    role="user",
                ),
            ]
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


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/auth/login",
        json={"username": username, "password": password},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def test_admin_can_manage_users_without_password_hash_leak(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}

    create_response = client.post(
        "/admin/users",
        headers=headers,
        json={"username": "guard", "password": "guard123", "role": "user"},
    )
    assert create_response.status_code == 201
    created_user = create_response.json()
    assert created_user["username"] == "guard"
    assert created_user["role"] == "user"
    assert "password_hash" not in created_user

    list_response = client.get("/admin/users", headers=headers)
    assert list_response.status_code == 200
    assert "password_hash" not in list_response.text
    assert {user["username"] for user in list_response.json()} == {
        "admin",
        "user",
        "guard",
    }

    update_response = client.put(
        f"/admin/users/{created_user['id']}",
        headers=headers,
        json={"role": "admin", "password": "newpass"},
    )
    assert update_response.status_code == 200
    assert update_response.json()["role"] == "admin"

    delete_response = client.delete(
        f"/admin/users/{created_user['id']}",
        headers=headers,
    )
    assert delete_response.status_code == 204


def test_user_role_cannot_manage_admin_users(client):
    token = _login(client, "user", "user123")

    response = client.get(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 403


def test_admin_cannot_delete_self(client):
    token = _login(client, "admin", "admin123")

    response = client.delete(
        "/admin/users/1",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot delete the current admin user"


def test_admin_user_create_rejects_duplicate_username(client):
    token = _login(client, "admin", "admin123")

    response = client.post(
        "/admin/users",
        headers={"Authorization": f"Bearer {token}"},
        json={"username": "user", "password": "another", "role": "user"},
    )

    assert response.status_code == 409
