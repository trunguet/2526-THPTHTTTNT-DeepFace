from dataclasses import dataclass

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from app.config.settings import settings
from app.db.schema import employees, face_embeddings
from app.ml.detector import require_face
from app.ml.embedder import create_face_embedding, create_face_embedding_from_face
from app.services.storage_service import resolved_image_file
from app.services.vector_store_service import (
    VectorSearchCandidate,
    VectorStoreNotFoundError,
    ensure_embedding_collection,
    search_face_embeddings,
    upsert_face_embedding,
)


class EmployeeNotFoundError(Exception):
    pass


class DuplicateFaceRegistrationError(Exception):
    pass


@dataclass(frozen=True)
class StoredEmbedding:
    id: int
    employee_id: int
    vector: list[float]
    model_name: str
    image_path: str
    source_image_key: str


def _find_duplicate_face(
    db: Session,
    *,
    employee_id: int,
    vector: list[float],
    model_name: str,
) -> tuple[VectorSearchCandidate, str, str] | None:
    ensure_embedding_collection(len(vector))
    try:
        candidates = search_face_embeddings(
            query_vector=vector,
            model_name=model_name,
            limit=5,
        )
    except VectorStoreNotFoundError:
        return None

    for candidate in candidates:
        if candidate.employee_id == employee_id:
            continue
        if candidate.score < settings.deepface_duplicate_threshold:
            continue

        employee = db.execute(
            select(employees.c.code, employees.c.name, employees.c.status).where(
                employees.c.id == candidate.employee_id,
            )
        ).first()
        if employee is None or employee.status != "active":
            continue

        return candidate, str(employee.code), str(employee.name)

    return None


def create_employee_embedding(
    db: Session,
    *,
    employee_id: int,
    image_path: str,
) -> StoredEmbedding:
    employee = db.execute(
        select(employees.c.id).where(employees.c.id == employee_id)
    ).first()
    if employee is None:
        raise EmployeeNotFoundError(f"Employee not found: {employee_id}")

    with resolved_image_file(image_path) as resolved_image:
        detection = require_face(resolved_image.normalized_path)
        face_image = getattr(detection, "face_image", None)
        embedding = (
            create_face_embedding_from_face(
                face_image,
                source_image_path=resolved_image.normalized_path,
            )
            if face_image is not None
            else create_face_embedding(resolved_image.normalized_path)
        )

    duplicate = _find_duplicate_face(
        db,
        employee_id=employee_id,
        vector=embedding.vector,
        model_name=embedding.model_name,
    )
    if duplicate is not None:
        candidate, employee_code, employee_name = duplicate
        raise DuplicateFaceRegistrationError(
            "Face already registered for "
            f"{employee_code} - {employee_name} "
            f"(score={candidate.score:.3f}, "
            f"threshold={settings.deepface_duplicate_threshold:.2f})."
        )

    result = db.execute(
        insert(face_embeddings).values(
            employee_id=employee_id,
            vector=embedding.vector,
            model_name=embedding.model_name,
            source_image_key=image_path,
        )
    )
    embedding_id = int(result.inserted_primary_key[0])
    try:
        upsert_face_embedding(
            embedding_id=embedding_id,
            employee_id=employee_id,
            vector=embedding.vector,
            model_name=embedding.model_name,
        )
    except Exception:
        db.rollback()
        raise

    db.commit()

    return StoredEmbedding(
        id=embedding_id,
        employee_id=employee_id,
        vector=embedding.vector,
        model_name=embedding.model_name,
        image_path=image_path,
        source_image_key=image_path,
    )
