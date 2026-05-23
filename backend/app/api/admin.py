import json
from pathlib import Path

from fastapi import APIRouter, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError

from app.config.redis import check_redis_connection, get_redis_client
from app.core.deps import AdminUser, DbSession
from app.core.security import hash_password
from app.db.health import check_database_connection
from app.repositories.user_repository import (
    create_user,
    delete_user,
    get_user_by_id,
    get_user_by_username,
    list_users,
)
from app.schemas.user import AdminUserCreate, AdminUserRead, AdminUserUpdate


router = APIRouter(prefix="/admin", tags=["admin"])
EVALUATION_REPORT_PATH = Path(__file__).resolve().parents[1] / "data" / "evaluation_report.json"


@router.get("/status")
def read_admin_status(current_user: AdminUser) -> dict[str, object]:
    database_ok, database_error = check_database_connection()
    redis_ok, redis_error = check_redis_connection()

    queue_lengths: dict[str, int] = {}
    if redis_ok:
        redis_client = get_redis_client()
        queue_lengths = {
            "embedding_jobs": int(redis_client.llen("embedding_jobs")),
            "access_jobs": int(redis_client.llen("access_jobs")),
        }

    return {
        "status": "ok" if database_ok and redis_ok else "degraded",
        "database": "ok" if database_ok else "error",
        "database_error": database_error,
        "redis": "ok" if redis_ok else "error",
        "redis_error": redis_error,
        "queue_lengths": queue_lengths,
    }


@router.get("/evaluation-report")
def read_evaluation_report(current_user: AdminUser) -> dict[str, object]:
    if not EVALUATION_REPORT_PATH.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Evaluation report not found",
        )

    try:
        with EVALUATION_REPORT_PATH.open(encoding="utf-8") as report_file:
            report = json.load(report_file)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Evaluation report is invalid",
        ) from exc

    return report


@router.get("/users", response_model=list[AdminUserRead])
def read_admin_users(db: DbSession, current_user: AdminUser) -> list[AdminUserRead]:
    return list_users(db)


@router.post(
    "/users",
    response_model=AdminUserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_admin_user(
    payload: AdminUserCreate,
    db: DbSession,
    current_user: AdminUser,
) -> AdminUserRead:
    existing_user = get_user_by_username(db, payload.username)
    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        )

    try:
        return create_user(
            db,
            username=payload.username,
            password_hash=hash_password(payload.password),
            role=payload.role,
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc


@router.put("/users/{user_id}", response_model=AdminUserRead)
def update_admin_user(
    user_id: int,
    payload: AdminUserUpdate,
    db: DbSession,
    current_user: AdminUser,
) -> AdminUserRead:
    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if payload.username is not None and payload.username != user.username:
        existing_user = get_user_by_username(db, payload.username)
        if existing_user is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already exists",
            )
        user.username = payload.username

    if payload.role is not None:
        user.role = payload.role

    if payload.password is not None:
        user.password_hash = hash_password(payload.password)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already exists",
        ) from exc

    db.refresh(user)
    return user


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admin_user(
    user_id: int,
    db: DbSession,
    current_user: AdminUser,
) -> Response:
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the current admin user",
        )

    user = get_user_by_id(db, user_id=user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    delete_user(db, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
