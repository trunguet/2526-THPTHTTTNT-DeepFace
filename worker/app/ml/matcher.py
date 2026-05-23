from dataclasses import dataclass
from math import sqrt
from typing import Sequence

from app.config.settings import settings

DEFAULT_MATCH_THRESHOLD = settings.deepface_match_threshold


@dataclass(frozen=True)
class MatchCandidate:
    employee_id: int
    vector: Sequence[float]
    model_name: str | None = None


@dataclass(frozen=True)
class MatchResult:
    matched: bool
    employee_id: int | None
    score: float | None
    threshold: float
    message: str


def cosine_similarity(first_vector: Sequence[float], second_vector: Sequence[float]) -> float:
    if not first_vector or not second_vector:
        raise ValueError("Vectors must not be empty.")

    if len(first_vector) != len(second_vector):
        raise ValueError("Vectors must have the same dimensions.")

    first_magnitude = sqrt(sum(value * value for value in first_vector))
    second_magnitude = sqrt(sum(value * value for value in second_vector))
    if first_magnitude == 0 or second_magnitude == 0:
        raise ValueError("Vectors must not have zero magnitude.")

    dot_product = sum(
        first_value * second_value
        for first_value, second_value in zip(first_vector, second_vector)
    )
    return round(dot_product / (first_magnitude * second_magnitude), 6)


def find_best_match(
    query_vector: Sequence[float],
    candidates: Sequence[MatchCandidate],
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> MatchResult:
    if not 0 <= threshold <= 1:
        raise ValueError("Match threshold must be between 0 and 1.")

    if not candidates:
        return MatchResult(
            matched=False,
            employee_id=None,
            score=None,
            threshold=threshold,
            message="No face embeddings available for matching.",
        )

    best_candidate: MatchCandidate | None = None
    best_score = -1.0
    for candidate in candidates:
        score = cosine_similarity(query_vector, candidate.vector)
        if score > best_score:
            best_score = score
            best_candidate = candidate

    if best_candidate is not None and best_score >= threshold:
        return MatchResult(
            matched=True,
            employee_id=best_candidate.employee_id,
            score=best_score,
            threshold=threshold,
            message="Face matched embedding.",
        )

    return MatchResult(
        matched=False,
        employee_id=best_candidate.employee_id if best_candidate else None,
        score=best_score if best_candidate else None,
        threshold=threshold,
        message="Best match is below threshold.",
    )
