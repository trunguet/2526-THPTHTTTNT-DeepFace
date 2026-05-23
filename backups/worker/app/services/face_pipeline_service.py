from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.db.schema import access_logs, employees, face_embeddings
from app.config.settings import settings
from app.ml.detector import require_face
from app.ml.embedder import create_face_embedding, create_face_embedding_from_face
from app.ml.matcher import DEFAULT_MATCH_THRESHOLD, MatchResult
from app.services.storage_service import resolved_image_file
from app.services.vector_store_service import VectorSearchCandidate, search_face_embeddings


class AccessLogNotFoundError(Exception):
    pass


@dataclass(frozen=True)
class AccessDecision:
    log_id: int
    status: str
    employee_id: int | None
    score: float | None
    image_path: str
    message: str


def _is_active_embedding_candidate(
    db: Session,
    *,
    candidate: VectorSearchCandidate,
) -> bool:
    row = db.execute(
        select(face_embeddings.c.id)
        .join(employees, employees.c.id == face_embeddings.c.employee_id)
        .where(face_embeddings.c.id == candidate.embedding_id)
        .where(face_embeddings.c.employee_id == candidate.employee_id)
        .where(employees.c.status == "active")
        .where(face_embeddings.c.model_name == candidate.model_name)
    ).first()
    return row is not None


def _find_best_active_qdrant_match(
    db: Session,
    *,
    query_vector: list[float],
    model_name: str,
    threshold: float,
) -> MatchResult:
    if not 0 <= threshold <= 1:
        raise ValueError("Match threshold must be between 0 and 1.")

    candidates = search_face_embeddings(
        query_vector=query_vector,
        model_name=model_name,
        limit=10,
    )

    for candidate in candidates:
        if not _is_active_embedding_candidate(db, candidate=candidate):
            continue

        if candidate.score >= threshold:
            return MatchResult(
                matched=True,
                employee_id=candidate.employee_id,
                score=candidate.score,
                threshold=threshold,
                message="Face matched embedding from Qdrant.",
            )

        return MatchResult(
            matched=False,
            employee_id=candidate.employee_id,
            score=candidate.score,
            threshold=threshold,
            message="Best Qdrant match is below threshold.",
        )

    return MatchResult(
        matched=False,
        employee_id=None,
        score=None,
        threshold=threshold,
        message="No active Qdrant face embeddings available for matching.",
    )


def _update_access_log(
    db: Session,
    *,
    log_id: int,
    status: str,
    employee_id: int | None,
    score: float | None,
    message: str,
) -> None:
    result = db.execute(
        update(access_logs)
        .where(access_logs.c.id == log_id)
        .values(status=status, employee_id=employee_id, score=score, message=message)
    )
    if result.rowcount == 0:
        db.rollback()
        raise AccessLogNotFoundError(f"Access log not found: {log_id}")

    db.commit()


def process_access_check(
    db: Session,
    *,
    log_id: int,
    image_path: str,
    threshold: float = DEFAULT_MATCH_THRESHOLD,
) -> AccessDecision:
    existing_log = db.execute(
        select(access_logs.c.id).where(access_logs.c.id == log_id)
    ).first()
    if existing_log is None:
        raise AccessLogNotFoundError(f"Access log not found: {log_id}")

    try:
        with resolved_image_file(image_path) as resolved_image:
            detection = require_face(
                resolved_image.normalized_path,
                detector_backend=settings.deepface_access_detector_backend,
            )
            face_image = getattr(detection, "face_image", None)
            embedding = (
                create_face_embedding_from_face(
                    face_image,
                    source_image_path=resolved_image.normalized_path,
                )
                if face_image is not None
                else create_face_embedding(resolved_image.normalized_path)
            )
            match = _find_best_active_qdrant_match(
                db,
                query_vector=embedding.vector,
                model_name=embedding.model_name,
                threshold=threshold,
            )

        if match.matched:
            status = "granted"
            employee_id = match.employee_id
        else:
            status = "denied"
            employee_id = None

        _update_access_log(
            db,
            log_id=log_id,
            status=status,
            employee_id=employee_id,
            score=match.score,
            message=match.message,
        )
        return AccessDecision(
            log_id=log_id,
            status=status,
            employee_id=employee_id,
            score=match.score,
            image_path=image_path,
            message=match.message,
        )
    except Exception as exc:
        _update_access_log(
            db,
            log_id=log_id,
            status="error",
            employee_id=None,
            score=None,
            message=str(exc),
        )
        return AccessDecision(
            log_id=log_id,
            status="error",
            employee_id=None,
            score=None,
            image_path=image_path,
            message=str(exc),
        )
