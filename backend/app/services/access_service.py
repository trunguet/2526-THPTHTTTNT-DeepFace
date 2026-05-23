from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.access_log import AccessLog
from app.queues.access_queue import AccessJob, enqueue_access_job
from app.repositories.access_log_repository import (
    count_processing_access_logs,
    create_access_log,
)
from app.repositories.camera_repository import get_camera_by_id
from app.schemas.access import AccessCheckRequest


class CameraNotFoundError(Exception):
    pass


class AccessQueueFullError(Exception):
    def __init__(self, *, camera_id: int, current_processing: int, limit: int):
        self.camera_id = camera_id
        self.current_processing = current_processing
        self.limit = limit
        super().__init__(
            "This camera already has too many frames waiting to be processed. "
            f"Please wait for the queue to drop below {limit} and try again."
        )


def check_access(db: Session, payload: AccessCheckRequest) -> tuple[AccessLog, AccessJob]:
    camera = get_camera_by_id(db, payload.camera_id)
    if camera is None:
        raise CameraNotFoundError

    processing_count = count_processing_access_logs(db, camera_id=camera.id)
    limit = settings.max_processing_access_logs_per_camera
    if processing_count >= limit:
        raise AccessQueueFullError(
            camera_id=camera.id,
            current_processing=processing_count,
            limit=limit,
        )

    access_log = create_access_log(
        db,
        employee_id=None,
        camera_id=camera.id,
        status="processing",
        score=None,
        image_path=payload.resolved_image_key,
        message="Access check queued. Worker will process it in background.",
    )
    job = enqueue_access_job(access_log.id, camera.id, payload.resolved_image_key)
    return access_log, job
