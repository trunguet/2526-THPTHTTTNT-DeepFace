import logging
from typing import Any

from app.config.database import get_db_session
from app.services.face_pipeline_service import process_access_check


def handle_access_job(payload: dict[str, Any]) -> None:
    job_id = payload.get("job_id")
    log_id = payload.get("log_id")
    camera_id = payload.get("camera_id")
    image_path = payload.get("image_key") or payload.get("image_path")

    if not job_id or not log_id or not camera_id or not image_path:
        raise ValueError(f"Invalid access job payload: {payload}")

    logging.info(
        "Received access job: job_id=%s log_id=%s camera_id=%s image_path=%s",
        job_id,
        log_id,
        camera_id,
        image_path,
    )
    with get_db_session() as db:
        decision = process_access_check(
            db,
            log_id=int(log_id),
            image_path=str(image_path),
        )

    logging.info(
        "Access job completed: job_id=%s log_id=%s status=%s employee_id=%s score=%s",
        job_id,
        log_id,
        decision.status,
        decision.employee_id,
        decision.score,
    )
