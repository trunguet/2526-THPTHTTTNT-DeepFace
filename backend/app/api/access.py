from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.deps import CurrentUser, DbSession
from app.schemas.access import (
    AccessCheckRequest,
    AccessCheckResponse,
    AccessSnapshotUploadResponse,
)
from app.services.access_service import (
    AccessQueueFullError,
    CameraNotFoundError,
    check_access,
)
from app.services.storage_service import UnsupportedImageTypeError, upload_fastapi_image


router = APIRouter(prefix="/access", tags=["access"])


@router.post(
    "/check",
    response_model=AccessCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def check_access_record(
    payload: AccessCheckRequest,
    db: DbSession,
    current_user: CurrentUser,
) -> AccessCheckResponse:
    try:
        access_log, job = check_access(db, payload)
    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        ) from exc
    except AccessQueueFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc

    return AccessCheckResponse(
        log_id=access_log.id,
        job_id=job.job_id,
        status=access_log.status,
        employee_id=access_log.employee_id,
        employee_name=access_log.employee_name,
        camera_id=access_log.camera_id,
        score=access_log.score,
        image_key=access_log.image_path,
        image_path=access_log.image_path,
        message=access_log.message or "Access check queued. Worker will process it in background.",
        created_at=access_log.created_at,
    )


@router.post(
    "/snapshots",
    response_model=AccessSnapshotUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_access_snapshot(
    current_user: CurrentUser,
    file: UploadFile = File(...),
) -> AccessSnapshotUploadResponse:
    try:
        stored_image = upload_fastapi_image(file, prefix="access-snapshots")
    except UnsupportedImageTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return AccessSnapshotUploadResponse(
        object_key=stored_image.object_key,
        bucket=stored_image.bucket,
        content_type=stored_image.content_type,
        size=stored_image.size,
    )


@router.post(
    "/check-image",
    response_model=AccessCheckResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def check_access_image(
    db: DbSession,
    current_user: CurrentUser,
    camera_id: int = Form(...),
    file: UploadFile = File(...),
) -> AccessCheckResponse:
    try:
        stored_image = upload_fastapi_image(file, prefix="access-snapshots")
        access_log, job = check_access(
            db,
            AccessCheckRequest(
                camera_id=camera_id,
                image_key=stored_image.object_key,
            ),
        )
    except CameraNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Camera not found",
        ) from exc
    except AccessQueueFullError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=str(exc),
        ) from exc
    except UnsupportedImageTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    return AccessCheckResponse(
        log_id=access_log.id,
        job_id=job.job_id,
        status=access_log.status,
        employee_id=access_log.employee_id,
        employee_name=access_log.employee_name,
        camera_id=access_log.camera_id,
        score=access_log.score,
        image_key=access_log.image_path,
        image_path=access_log.image_path,
        message=access_log.message or "Image uploaded and access check queued.",
        created_at=access_log.created_at,
    )
