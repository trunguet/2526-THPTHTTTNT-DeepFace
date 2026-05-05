from dataclasses import dataclass
from typing import Any

import numpy as np

from app.config import MATCH_THRESHOLD, QDRANT_COLLECTION


@dataclass(frozen=True)
class MatchResult:
    employee_id: str | None
    score: float
    payload: dict[str, Any]
    matched: bool


def qdrant_score(result: Any) -> float:
    return float(getattr(result, "score", 0.0) or 0.0)


def qdrant_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "payload", None)
    return payload if isinstance(payload, dict) else {}


class QdrantFaceMatcher:
    def __init__(self, threshold: float = MATCH_THRESHOLD, collection_name: str = QDRANT_COLLECTION):
        self.threshold = threshold
        self.collection_name = collection_name

    def match(self, embedding: np.ndarray, limit: int = 1) -> MatchResult:
        from app.vector_store import search_face

        results = search_face(embedding.astype(np.float32).tolist(), limit=limit)
        top = results[0] if results else None
        if top is None:
            return MatchResult(employee_id=None, score=0.0, payload={}, matched=False)

        score = qdrant_score(top)
        payload = qdrant_payload(top)
        employee_id = str(payload["employee_id"]) if payload.get("employee_id") is not None else None

        return MatchResult(
            employee_id=employee_id if score >= self.threshold else None,
            score=score,
            payload=payload,
            matched=bool(employee_id and score >= self.threshold),
        )
