import time

from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, PointIdsList, PointStruct, VectorParams

from app.config import QDRANT_COLLECTION, QDRANT_URL, VECTOR_SIZE


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(url=QDRANT_URL)


def init_collection(retries: int = 20) -> None:
    client = get_qdrant_client()
    for attempt in range(retries):
        try:
            collections = client.get_collections().collections
            names = {collection.name for collection in collections}
            if QDRANT_COLLECTION not in names:
                client.create_collection(
                    collection_name=QDRANT_COLLECTION,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def upsert_employee_vector(employee_id: int, vector: list[float], payload: dict) -> None:
    client = get_qdrant_client()
    client.upsert(
        collection_name=QDRANT_COLLECTION,
        points=[PointStruct(id=employee_id, vector=vector, payload=payload)],
    )


def delete_employee_vector(employee_id: int) -> None:
    client = get_qdrant_client()
    client.delete(
        collection_name=QDRANT_COLLECTION,
        points_selector=PointIdsList(points=[employee_id]),
    )


def search_face(vector: list[float], limit: int = 1):
    client = get_qdrant_client()
    if hasattr(client, "search"):
        return client.search(
            collection_name=QDRANT_COLLECTION,
            query_vector=vector,
            limit=limit,
            with_payload=True,
        )

    result = client.query_points(
        collection_name=QDRANT_COLLECTION,
        query=vector,
        limit=limit,
        with_payload=True,
    )
    return result.points
