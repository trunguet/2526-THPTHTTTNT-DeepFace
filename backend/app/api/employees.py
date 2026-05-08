from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import build_embedding, validate_image
from app.db import AttendanceLog, Employee, EmployeeBackup, get_db
from app.jobs import enqueue_embedding_job
from app.schemas import EmployeeCreate, EmployeeUpdate
from app.storage import delete_object, read_bytes, save_bytes
from app.vector_store import delete_employee_vector, upsert_employee_vector


router = APIRouter(prefix="/api/employees", tags=["employees"])


def _resolve_employee(db: Session, identifier: str) -> Employee | None:
    """
    Resolve an employee by business identifier first (`employee_code`), then fall back to DB id.
    This keeps backward compatibility for older clients that used numeric DB ids.
    """
    value = str(identifier or "").strip()
    if not value:
        return None

    employee = db.query(Employee).filter(Employee.employee_code == value).first()
    if employee is not None:
        return employee

    if value.isdigit():
        return db.query(Employee).filter(Employee.id == int(value)).first()
    return None


def _employee_to_dict(employee: Employee) -> dict[str, Any]:
    image_url = f"/api/files/{employee.minio_image_path}" if employee.minio_image_path else ""
    business_id = employee.employee_code or str(employee.id)
    return {
        "id": employee.id,
        "employee_id": business_id,
        "full_name": employee.full_name,
        "email": employee.email or "",
        "department": employee.department or "",
        "image_url": image_url,
        "image_object_key": employee.minio_image_path,
        "embedding_status": "indexed" if employee.is_vectorized else "pending",
        "created_at": employee.created_at,
    }


def _object_key_from_url(image_url: str) -> str:
    marker = "/api/files/"
    if marker in image_url:
        return image_url.split(marker, 1)[1]
    return ""


def _index_employee(employee: Employee, db: Session) -> None:
    if not employee.minio_image_path:
        raise HTTPException(status_code=400, detail="Employee has no uploaded image")

    image_bytes = read_bytes(employee.minio_image_path)
    vector = build_embedding(image_bytes)
    business_id = employee.employee_code or str(employee.id)
    upsert_employee_vector(
        employee.id,
        vector,
        {
            "db_id": employee.id,
            "employee_id": business_id,
            "full_name": employee.full_name,
        },
    )
    employee.is_vectorized = True
    db.commit()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), employee_id: str = Form(...)) -> dict[str, str]:
    employee_id = str(employee_id or "").strip()
    if not employee_id:
        raise HTTPException(status_code=400, detail="Employee ID is required")
    if len(employee_id) > 50:
        raise HTTPException(status_code=400, detail="Employee ID is too long (max 50 characters)")
    content = await file.read()
    try:
        validate_image(content)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image file: {exc}")

    object_key, image_url = save_bytes(f"employees/{employee_id}", content, file.content_type or "image/jpeg")
    return {"image_url": image_url, "image_object_key": object_key}


@router.post("")
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> dict[str, Any]:
    image_object_key = payload.image_object_key or _object_key_from_url(payload.image_url)
    business_id = str(payload.employee_id or "").strip()
    if not business_id:
        raise HTTPException(status_code=400, detail="Employee ID is required")
    if len(business_id) > 50:
        raise HTTPException(status_code=400, detail="Employee ID is too long (max 50 characters)")
    employee = Employee(
        employee_code=business_id,
        full_name=payload.full_name,
        email=(payload.email or "").strip() or None,
        department=(payload.department or "").strip() or None,
        minio_image_path=image_object_key,
        is_vectorized=False,
    )
    db.add(employee)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Employee ID already exists")

    db.refresh(employee)
    try:
        enqueue_embedding_job(employee.id)
    except Exception as exc:
        print(f"[WARN] Failed to enqueue embedding job for employee {employee.id}: {exc}", flush=True)

    return _employee_to_dict(employee)


@router.get("")
def list_employees(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    employees = db.query(Employee).order_by(Employee.id.desc()).all()
    return [_employee_to_dict(employee) for employee in employees]


@router.get("/unscanned-today")
def list_unscanned_today(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Return employees that the system has not "seen" today, i.e. there is no
    attendance log row linked to the employee for today's Vietnam-local date.

    Note: Attendance logs can be linked either by successful recognition or by
    a client-provided employee identifier for failed attempts. This endpoint
    checks linkage, not recognition success.
    The DB connection sets `time_zone = +07:00`, so CURDATE()/DATE(scan_time)
    align with Vietnam time.
    """

    start_of_day = func.curdate()
    end_of_day = func.date_add(func.curdate(), text("INTERVAL 1 DAY"))
    scanned_today = (
        db.query(AttendanceLog.id)
        .filter(AttendanceLog.employee_code == Employee.employee_code)
        .filter(AttendanceLog.scan_time >= start_of_day)
        .filter(AttendanceLog.scan_time < end_of_day)
    )

    employees = (
        db.query(Employee)
        .filter(~scanned_today.exists())
        .order_by(Employee.full_name.asc(), Employee.employee_code.asc())
        .all()
    )

    today = db.query(func.curdate()).scalar()
    return {
        "date": str(today) if today is not None else "",
        "count": len(employees),
        "items": [
            {
                "id": employee.id,
                "employee_id": employee.employee_code,
                "full_name": employee.full_name,
                "email": employee.email or "",
                "department": employee.department or "",
                "created_at": employee.created_at,
            }
            for employee in employees
        ],
    }


@router.put("/{employee_id}")
def update_employee(employee_id: str, payload: EmployeeUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    employee = _resolve_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    if payload.full_name is not None:
        db.add(
            EmployeeBackup(
                original_id=employee.id,
                full_name=employee.full_name,
                minio_image_path=employee.minio_image_path,
                action_type="UPDATE",
            )
        )
        employee.full_name = payload.full_name.strip()
    if payload.email is not None:
        employee.email = payload.email.strip() or None
    if payload.department is not None:
        employee.department = payload.department.strip() or None
    db.commit()
    db.refresh(employee)

    if employee.is_vectorized:
        try:
            _index_employee(employee, db)
        except Exception as exc:
            print(f"[WARN] Failed to refresh Qdrant payload for employee {employee.id}: {exc}", flush=True)

    return _employee_to_dict(employee)


@router.delete("/{employee_id}")
def delete_employee(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = _resolve_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    object_key = employee.minio_image_path
    vector_id = employee.id
    db.add(
        EmployeeBackup(
            original_id=employee.id,
            full_name=employee.full_name,
            minio_image_path=employee.minio_image_path,
            action_type="DELETE",
        )
    )
    db.delete(employee)
    db.commit()

    try:
        delete_employee_vector(vector_id)
    except Exception as exc:
        print(f"[WARN] Failed to delete Qdrant vector for employee {vector_id}: {exc}", flush=True)
    try:
        delete_object(object_key)
    except Exception as exc:
        print(f"[WARN] Failed to delete employee image {object_key}: {exc}", flush=True)

    return {"status": "ok"}


@router.post("/{employee_id}/extract-embedding")
def extract_embedding(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = _resolve_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        _index_employee(employee, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding extraction failed: {exc}")
    return {"status": "ok"}


@router.get("/{employee_id}/access-history")
def access_history(employee_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    employee = _resolve_employee(db, employee_id)
    if employee is None:
        return []

    rows = (
        db.query(AttendanceLog)
        .filter(AttendanceLog.employee_code == employee.employee_code)
        .order_by(AttendanceLog.scan_time.desc())
        .all()
    )
    return [
        {
            "timestamp": row.scan_time,
            "access_type": "check_in",
            "status": "allowed" if row.status == "SUCCESS" else "denied",
            "camera_location": "N/A",
        }
        for row in rows
    ]
