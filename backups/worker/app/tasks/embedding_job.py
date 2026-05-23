import logging
from typing import Any

from sqlalchemy import update

from app.config.database import get_db_session
from app.db.schema import employees
from app.services.embedding_service import create_employee_embedding


def _set_embedding_status(
    db,
    *,
    employee_id: int,
    status: str,
    error: str | None = None,
) -> None:
    db.execute(
        update(employees)
        .where(employees.c.id == employee_id)
        .values(
            embedding_status=status,
            embedding_error=error[:1000] if error is not None else None,
        )
    )
    db.commit()


def handle_embedding_job(payload: dict[str, Any]) -> None:
    job_id = payload.get("job_id")
    employee_id = payload.get("employee_id")
    image_path = payload.get("image_key") or payload.get("image_path")

    if not job_id or not employee_id or not image_path:
        raise ValueError(f"Invalid embedding job payload: {payload}")

    logging.info(
        "Received embedding job: job_id=%s employee_id=%s image_path=%s",
        job_id,
        employee_id,
        image_path,
    )
    employee_id_int = int(employee_id)
    with get_db_session() as db:
        try:
            embedding = create_employee_embedding(
                db,
                employee_id=employee_id_int,
                image_path=str(image_path),
            )
            _set_embedding_status(
                db,
                employee_id=employee_id_int,
                status="success",
                error=None,
            )
        except Exception as exc:
            db.rollback()
            _set_embedding_status(
                db,
                employee_id=employee_id_int,
                status="error",
                error=str(exc),
            )
            raise

    logging.info(
        "Embedding job completed: job_id=%s employee_id=%s embedding_id=%s model=%s",
        job_id,
        employee_id,
        embedding.id,
        embedding.model_name,
    )
