import pytest

from app.services import vector_store_service
from app.services.vector_store_service import (
    VectorStoreNotFoundError,
    VectorStoreError,
    ensure_embedding_collection,
    search_face_embeddings,
    upsert_face_embedding,
)


def test_ensure_embedding_collection_creates_missing_collection(monkeypatch):
    calls = []

    def fake_request_json(method: str, path: str, *, body=None):
        calls.append({"method": method, "path": path, "body": body})
        if method == "GET":
            raise VectorStoreNotFoundError("missing collection")
        return {"status": "ok"}

    monkeypatch.setattr(vector_store_service, "_request_json", fake_request_json)

    ensure_embedding_collection(3)

    assert calls[1]["method"] == "PUT"
    assert calls[1]["body"] == {
        "vectors": {
            "size": 3,
            "distance": "Cosine",
        },
    }


def test_ensure_embedding_collection_rejects_wrong_vector_size(monkeypatch):
    def fake_request_json(method: str, path: str, *, body=None):
        return {
            "status": "ok",
            "result": {
                "config": {
                    "params": {
                        "vectors": {
                            "size": 512,
                        }
                    }
                }
            },
        }

    monkeypatch.setattr(vector_store_service, "_request_json", fake_request_json)

    with pytest.raises(VectorStoreError, match="vector size"):
        ensure_embedding_collection(3)


def test_upsert_face_embedding_writes_point_payload(monkeypatch):
    calls = []
    monkeypatch.setattr(vector_store_service, "ensure_embedding_collection", lambda size: None)

    def fake_request_json(method: str, path: str, *, body=None):
        calls.append({"method": method, "path": path, "body": body})
        return {"status": "ok"}

    monkeypatch.setattr(vector_store_service, "_request_json", fake_request_json)

    upsert_face_embedding(
        embedding_id=10,
        employee_id=1,
        vector=[1.0, 0.0, 0.0],
        model_name="Facenet512",
    )

    assert calls == [
        {
            "method": "PUT",
            "path": "/collections/deepface_embeddings/points?wait=true",
            "body": {
                "points": [
                    {
                        "id": 10,
                        "vector": [1.0, 0.0, 0.0],
                        "payload": {
                            "embedding_id": 10,
                            "employee_id": 1,
                            "model_name": "Facenet512",
                        },
                    }
                ]
            },
        }
    ]


def test_search_face_embeddings_maps_qdrant_results(monkeypatch):
    def fake_request_json(method: str, path: str, *, body=None):
        assert method == "POST"
        assert body["filter"]["must"][0]["match"]["value"] == "Facenet512"
        return {
            "result": [
                {
                    "id": 10,
                    "score": 0.91,
                    "payload": {
                        "embedding_id": 10,
                        "employee_id": 1,
                        "model_name": "Facenet512",
                    },
                }
            ]
        }

    monkeypatch.setattr(vector_store_service, "_request_json", fake_request_json)

    candidates = search_face_embeddings(
        query_vector=[1.0, 0.0, 0.0],
        model_name="Facenet512",
    )

    assert len(candidates) == 1
    assert candidates[0].embedding_id == 10
    assert candidates[0].employee_id == 1
    assert candidates[0].score == 0.91
