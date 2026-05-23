from fastapi.testclient import TestClient
from types import SimpleNamespace

from app.core.deps import get_current_user
from app.main import app


class FakeRedis:
    def __init__(self, lengths: dict[str, int] | None = None):
        self.lengths = lengths or {}

    def llen(self, queue_name: str) -> int:
        return self.lengths.get(queue_name, 0)


def test_health_check_reports_ok_when_dependencies_are_available(monkeypatch):
    monkeypatch.setattr("app.main.check_database_connection", lambda: (True, None))
    monkeypatch.setattr("app.main.check_redis_connection", lambda: (True, None))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["redis"] == "ok"


def test_health_check_reports_503_when_dependency_is_unavailable(monkeypatch):
    monkeypatch.setattr(
        "app.main.check_database_connection",
        lambda: (False, "OperationalError"),
    )
    monkeypatch.setattr("app.main.check_redis_connection", lambda: (True, None))

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json()["status"] == "error"
    assert response.json()["database"] == "error"
    assert response.json()["database_error"] == "OperationalError"
    assert response.json()["redis"] == "ok"


def test_metrics_exposes_core_prometheus_metrics(monkeypatch):
    monkeypatch.setattr("app.main.check_database_connection", lambda: (False, None))
    monkeypatch.setattr("app.main.check_redis_connection", lambda: (True, None))
    monkeypatch.setattr(
        "app.main.get_redis_client",
        lambda: FakeRedis({"embedding_jobs": 2, "access_jobs": 3}),
    )

    with TestClient(app) as client:
        response = client.get("/metrics")

    assert response.status_code == 200
    body = response.text
    assert "deepface_backend_up 1" in body
    assert "deepface_database_up 0" in body
    assert "deepface_redis_up 1" in body
    assert 'deepface_queue_length{queue="embedding_jobs"} 2' in body
    assert 'deepface_queue_length{queue="access_jobs"} 3' in body


def test_admin_status_reports_queue_lengths(monkeypatch):
    monkeypatch.setattr("app.api.admin.check_database_connection", lambda: (True, None))
    monkeypatch.setattr("app.api.admin.check_redis_connection", lambda: (True, None))
    monkeypatch.setattr(
        "app.api.admin.get_redis_client",
        lambda: FakeRedis({"embedding_jobs": 4, "access_jobs": 5}),
    )

    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    try:
        with TestClient(app) as client:
            response = client.get("/admin/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "database_error": None,
        "redis": "ok",
        "redis_error": None,
        "queue_lengths": {
            "embedding_jobs": 4,
            "access_jobs": 5,
        },
    }


def test_admin_status_rejects_user_role(monkeypatch):
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="user")
    try:
        with TestClient(app) as client:
            response = client.get("/admin/status")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"


def test_admin_evaluation_report_returns_internal_metrics():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="admin")
    try:
        with TestClient(app) as client:
            response = client.get("/admin/evaluation-report")
    finally:
        app.dependency_overrides.clear()

    body = response.json()
    assert response.status_code == 200
    assert body["dataset"]["subjects"] >= 3
    assert body["dataset"]["total_cases"] == (
        body["metrics"]["correct"] + body["metrics"]["wrong"] + body["metrics"]["rejected"]
    )
    assert body["metrics"]["average_access_seconds"] > 0


def test_admin_evaluation_report_rejects_user_role():
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(role="user")
    try:
        with TestClient(app) as client:
            response = client.get("/admin/evaluation-report")
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin role required"
