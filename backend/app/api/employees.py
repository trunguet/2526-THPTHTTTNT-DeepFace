from fastapi import APIRouter, File, HTTPException, Response, UploadFile, status

from app.core.deps import AdminUser, DbSession
from app.schemas.employee import (
    EmployeeCreate,
    EmployeeEmbeddingJobRequest,
    EmployeeEmbeddingJobResponse,
    EmployeeRead,
    EmployeeUpdate,
    ImageUploadResponse,
)
from app.services.employee_service import (
    EmployeeCodeAlreadyExistsError,
    EmployeeNotFoundError,
    add_employee,
    delete_employee,
    edit_employee,
    get_embedding_queue_name,
    get_employee,
    get_employees,
    queue_employee_embedding_job,
)
from app.services.storage_service import UnsupportedImageTypeError, upload_fastapi_image


router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[EmployeeRead])
def list_employee_records(
    db: DbSession,
    current_user: AdminUser,
) -> list[EmployeeRead]:
    return get_employees(db)


@router.post("", response_model=EmployeeRead, status_code=status.HTTP_201_CREATED)
def create_employee_record(
    payload: EmployeeCreate,
    db: DbSession,
    current_user: AdminUser,
) -> EmployeeRead:
    try:
        return add_employee(db, payload)
    except EmployeeCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code already exists",
        ) from exc


@router.get("/{employee_id}", response_model=EmployeeRead)
def read_employee_record(
    employee_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> EmployeeRead:
    employee = get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.put("/{employee_id}", response_model=EmployeeRead)
def update_employee_record(
    employee_id: int,
    payload: EmployeeUpdate,
    db: DbSession,
    current_user: AdminUser,
) -> EmployeeRead:
    try:
        employee = edit_employee(db, employee_id, payload)
    except EmployeeCodeAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Employee code already exists",
        ) from exc

    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return employee


@router.delete("/{employee_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_employee_record(
    employee_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> Response:
    employee = delete_employee(db, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{employee_id}/embedding-jobs",
    response_model=EmployeeEmbeddingJobResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
def create_employee_embedding_job(
    employee_id: int,
    payload: EmployeeEmbeddingJobRequest,
    db: DbSession,
    current_user: AdminUser,
) -> EmployeeEmbeddingJobResponse:
    try:
        job = queue_employee_embedding_job(db, employee_id, payload.resolved_image_key)
    except EmployeeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        ) from exc

    return EmployeeEmbeddingJobResponse(
        job_id=job.job_id,
        type=job.type,
        employee_id=job.employee_id,
        image_key=job.image_key or job.image_path,
        image_path=job.image_path,
        queue_name=get_embedding_queue_name(),
        message="Embedding job queued. Worker will process it in background.",
    )


@router.post(
    "/{employee_id}/face-image",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
def upload_employee_face_image(
    employee_id: int,
    db: DbSession,
    current_user: AdminUser,
    file: UploadFile = File(...),
) -> ImageUploadResponse:
    employee = get_employee(db, employee_id)
    if employee is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Employee not found",
        )

    try:
        stored_image = upload_fastapi_image(
            file,
            prefix=f"employee-faces/{employee_id}",
        )
        job = queue_employee_embedding_job(db, employee_id, stored_image.object_key)
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

    return ImageUploadResponse(
        object_key=stored_image.object_key,
        bucket=stored_image.bucket,
        content_type=stored_image.content_type,
        size=stored_image.size,
        job_id=job.job_id,
        type=job.type,
        employee_id=job.employee_id,
        queue_name=get_embedding_queue_name(),
        message="Image uploaded and embedding job queued.",
    )
