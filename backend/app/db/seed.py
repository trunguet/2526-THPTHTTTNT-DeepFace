from os import getenv

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.db.init_db import create_tables
from app.db.session import SessionLocal
from app.models.access_log import AccessLog
from app.models.camera import Camera
from app.models.employee import Employee
from app.models.user import User


DEMO_USERS = [
    {
        "username": getenv("SEED_ADMIN_USERNAME", "admin"),
        "password": getenv("SEED_ADMIN_PASSWORD", "admin123"),
        "role": "admin",
    },
    {
        "username": getenv("SEED_USER_USERNAME", "user"),
        "password": getenv("SEED_USER_PASSWORD", "user123"),
        "role": "user",
    },
]

DEMO_CAMERAS = [
    {
        "name": "Main Gate",
        "location": "Company lobby",
        "stream_url": "rtsp://demo.local/main-gate",
        "status": "active",
    },
]

OBSOLETE_DEMO_CAMERAS = [
    {
        "name": "Back Door",
        "stream_url": "rtsp://demo.local/back-door",
    },
]

DEMO_EMPLOYEES = [
    {
        "code": "EMP001",
        "name": "Nguyen Van A",
        "department": "Engineering",
        "status": "active",
        "embedding_status": "none",
    },
    {
        "code": "EMP002",
        "name": "Tran Thi B",
        "department": "Operations",
        "status": "active",
        "embedding_status": "none",
    },
    {
        "code": "EMP003",
        "name": "Le Van C",
        "department": "Security",
        "status": "inactive",
        "embedding_status": "none",
    },
]

DEMO_ACCESS_LOGS = [
    {
        "employee_code": "EMP001",
        "camera_name": "Main Gate",
        "status": "granted",
        "score": 0.86,
        "image_path": "demo/access-snapshots/granted-main-gate.jpg",
        "message": "Demo granted access log.",
    },
    {
        "employee_code": None,
        "camera_name": "Main Gate",
        "status": "denied",
        "score": 0.42,
        "image_path": "demo/access-snapshots/denied-main-gate.jpg",
        "message": "Demo denied access log.",
    },
    {
        "employee_code": None,
        "camera_name": "Main Gate",
        "status": "error",
        "score": None,
        "image_path": "demo/access-snapshots/no-face.jpg",
        "message": "Demo error log for an image without a detectable face.",
    },
]


def seed_users(db: Session) -> int:
    created_count = 0

    for demo_user in DEMO_USERS:
        existing_user = db.scalar(
            select(User).where(User.username == demo_user["username"])
        )
        if existing_user is not None:
            continue

        db.add(
            User(
                username=demo_user["username"],
                password_hash=hash_password(demo_user["password"]),
                role=demo_user["role"],
            )
        )
        created_count += 1

    db.commit()
    return created_count


def seed_demo_records(db: Session) -> dict[str, int]:
    created_counts = {"cameras": 0, "employees": 0, "access_logs": 0}

    for obsolete_camera in OBSOLETE_DEMO_CAMERAS:
        existing_camera = db.scalar(
            select(Camera).where(Camera.name == obsolete_camera["name"])
        )
        if (
            existing_camera is not None
            and existing_camera.stream_url == obsolete_camera["stream_url"]
            and existing_camera.status != "inactive"
        ):
            existing_camera.status = "inactive"

    primary_camera_config = DEMO_CAMERAS[0]
    primary_camera = db.scalar(select(Camera).order_by(Camera.id.asc()).limit(1))
    if primary_camera is None:
        primary_camera = Camera(**primary_camera_config)
        db.add(primary_camera)
        db.flush()
        created_counts["cameras"] += 1
    else:
        primary_camera.name = primary_camera_config["name"]
        primary_camera.location = primary_camera_config["location"]
        primary_camera.stream_url = primary_camera_config["stream_url"]
        primary_camera.status = primary_camera_config["status"]

    db.flush()

    extra_cameras = list(
        db.scalars(
            select(Camera)
            .where(Camera.id != primary_camera.id)
            .order_by(Camera.id.asc())
        )
    )
    if extra_cameras:
        extra_camera_ids = [camera.id for camera in extra_cameras]
        access_logs = list(
            db.scalars(
                select(AccessLog).where(AccessLog.camera_id.in_(extra_camera_ids))
            )
        )
        for access_log in access_logs:
            access_log.camera_id = primary_camera.id

        for extra_camera in extra_cameras:
            db.delete(extra_camera)

    for demo_employee in DEMO_EMPLOYEES:
        existing_employee = db.scalar(
            select(Employee).where(Employee.code == demo_employee["code"])
        )
        if existing_employee is not None:
            continue

        db.add(Employee(**demo_employee))
        created_counts["employees"] += 1

    db.commit()

    existing_log_count = db.scalar(select(func.count(AccessLog.id))) or 0
    if existing_log_count > 0:
        return created_counts

    employees_by_code = {
        employee.code: employee
        for employee in db.scalars(select(Employee)).all()
    }
    cameras_by_name = {primary_camera.name: primary_camera}

    for demo_log in DEMO_ACCESS_LOGS:
        employee_code = demo_log["employee_code"]
        camera_name = demo_log["camera_name"]
        employee = employees_by_code.get(employee_code) if employee_code else None
        camera = cameras_by_name.get(camera_name) if camera_name else None

        db.add(
            AccessLog(
                employee_id=employee.id if employee is not None else None,
                camera_id=camera.id if camera is not None else None,
                status=demo_log["status"],
                score=demo_log["score"],
                image_path=demo_log["image_path"],
                message=demo_log["message"],
            )
        )
        created_counts["access_logs"] += 1

    db.commit()
    return created_counts


def should_seed_demo_data() -> bool:
    return getenv("SEED_DEMO_DATA", "true").strip().lower() not in {
        "0",
        "false",
        "no",
        "off",
    }


def main() -> None:
    try:
        create_tables()
        with SessionLocal() as db:
            created_users = seed_users(db)
            demo_counts = (
                seed_demo_records(db)
                if should_seed_demo_data()
                else {"cameras": 0, "employees": 0, "access_logs": 0}
            )
    except SQLAlchemyError as exc:
        raise SystemExit(f"Database seed failed: {exc}") from exc

    print(
        "Seed data is ready. "
        f"Created users: {created_users}; "
        f"cameras: {demo_counts['cameras']}; "
        f"employees: {demo_counts['employees']}; "
        f"access_logs: {demo_counts['access_logs']}."
    )


if __name__ == "__main__":
    main()
