from sqlalchemy.orm import Session

from app.models.camera import Camera
from app.repositories.camera_repository import (
    get_first_camera,
    get_camera_by_id,
    get_latest_active_camera,
    list_cameras,
)


def get_cameras(db: Session) -> list[Camera]:
    return list_cameras(db)


def get_camera(db: Session, camera_id: int) -> Camera | None:
    return get_camera_by_id(db, camera_id)


def get_default_active_camera(db: Session) -> Camera | None:
    return get_first_camera(db) or get_latest_active_camera(db)
