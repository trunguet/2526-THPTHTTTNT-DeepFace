from fastapi import APIRouter, HTTPException, status

from app.core.deps import AdminUser, CurrentUser, DbSession
from app.schemas.camera import CameraCreate, CameraRead, CameraUpdate
from app.services.camera_service import (
    get_default_active_camera,
    get_camera,
    get_cameras,
)


router = APIRouter(prefix="/cameras", tags=["cameras"])

CAMERA_READ_ONLY_MESSAGE = (
    "Camera management is read-only in the current version. The system uses a single built-in gate camera."
)


@router.get("/active-default", response_model=CameraRead)
def read_default_active_camera(
    db: DbSession,
    current_user: CurrentUser,
) -> CameraRead:
    camera = get_default_active_camera(db)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active camera is configured",
        )

    return camera


@router.get("", response_model=list[CameraRead])
def list_camera_records(
    db: DbSession,
    current_user: AdminUser,
) -> list[CameraRead]:
    return get_cameras(db)


@router.post("", response_model=CameraRead, status_code=status.HTTP_201_CREATED)
def create_camera_record(
    payload: CameraCreate,
    db: DbSession,
    current_user: AdminUser,
) -> CameraRead:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=CAMERA_READ_ONLY_MESSAGE,
    )


@router.get("/{camera_id}", response_model=CameraRead)
def read_camera_record(
    camera_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> CameraRead:
    camera = get_camera(db, camera_id)
    if camera is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        )

    return camera


@router.put("/{camera_id}", response_model=CameraRead)
def update_camera_record(
    camera_id: int,
    payload: CameraUpdate,
    db: DbSession,
    current_user: AdminUser,
) -> CameraRead:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=CAMERA_READ_ONLY_MESSAGE,
    )


@router.delete("/{camera_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_camera_record(
    camera_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> None:
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail=CAMERA_READ_ONLY_MESSAGE,
    )
