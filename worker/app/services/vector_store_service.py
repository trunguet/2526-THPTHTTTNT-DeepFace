import json
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config.qdrant import qdrant_settings


class VectorStoreError(Exception):
    pass


class VectorStoreNotFoundError(VectorStoreError):
    pass


@dataclass(frozen=True)
class VectorSearchCandidate:
    embedding_id: int
    employee_id: int
    score: float
    model_name: str


def _request_json(
    method: str,
    path: str,
    *,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    url = f"{qdrant_settings.url.rstrip('/')}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")

    request = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=10) as response:
            raw_body = response.read()
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code == 404:
            raise VectorStoreNotFoundError(
                f"Qdrant resource was not found: {method} {path}"
            ) from exc
        raise VectorStoreError(
            f"Qdrant request failed: {method} {path} -> {exc.code}: {detail}"
        ) from exc
    except URLError as exc:
        raise VectorStoreError(f"Qdrant is not reachable: {exc.reason}") from exc

    if not raw_body:
        return {}

    try:
        return json.loads(raw_body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise VectorStoreError("Qdrant returned invalid JSON.") from exc


def _collection_path() -> str:
    return f"/collections/{quote(qdrant_settings.collection, safe='')}"


def ensure_embedding_collection(vector_size: int) -> None:
    if vector_size <= 0:
        raise VectorStoreError("Vector size must be greater than zero.")

    try:
        response = _request_json("GET", _collection_path())
    except VectorStoreNotFoundError:
        response = {}

    if response.get("status") == "ok":
        configured_size = (
            response.get("result", {})
            .get("config", {})
            .get("params", {})
            .get("vectors", {})
            .get("size")
        )
        if configured_size is not None and int(configured_size) != vector_size:
            raise VectorStoreError(
                "Qdrant collection vector size does not match the embedding size."
            )
        return

    _request_json(
        "PUT",
        _collection_path(),
        body={
            "vectors": {
                "size": vector_size,
                "distance": "Cosine",
            },
        },
    )


def upsert_face_embedding(
    *,
    embedding_id: int,
    employee_id: int,
    vector: list[float],
    model_name: str,
) -> None:
    ensure_embedding_collection(len(vector))
    _request_json(
        "PUT",
        f"{_collection_path()}/points?wait=true",
        body={
            "points": [
                {
                    "id": embedding_id,
                    "vector": vector,
                    "payload": {
                        "embedding_id": embedding_id,
                        "employee_id": employee_id,
                        "model_name": model_name,
                    },
                }
            ]
        },
    )


def search_face_embeddings(
    *,
    query_vector: list[float],
    model_name: str,
    limit: int = 10,
) -> list[VectorSearchCandidate]:
    if limit <= 0:
        raise VectorStoreError("Search limit must be greater than zero.")

    response = _request_json(
        "POST",
        f"{_collection_path()}/points/search",
        body={
            "vector": query_vector,
            "limit": limit,
            "with_payload": True,
            "filter": {
                "must": [
                    {
                        "key": "model_name",
                        "match": {
                            "value": model_name,
                        },
                    }
                ]
            },
        },
    )

    candidates: list[VectorSearchCandidate] = []
    for item in response.get("result", []):
        payload = item.get("payload") or {}
        if payload.get("employee_id") is None:
            continue

        candidates.append(
            VectorSearchCandidate(
                embedding_id=int(payload.get("embedding_id", item["id"])),
                employee_id=int(payload["employee_id"]),
                score=round(float(item["score"]), 6),
                model_name=str(payload.get("model_name", model_name)),
            )
        )

    return candidates
