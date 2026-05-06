from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import build_embedding, validate_image
from app.db import AttendanceLog, Employee, EmployeeBackup, get_db, now_utc
from app.jobs import enqueue_embedding_job
from app.schemas import EmployeeCreate, EmployeeUpdate
from app.storage import delete_object, read_bytes, save_bytes
from app.vector_store import delete_employee_vector, upsert_employee_vector


router = APIRouter(prefix="/api/employees", tags=["employees"])


def _employee_to_dict(employee: Employee) -> dict[str, Any]:
    image_url = f"/api/files/{employee.minio_image_path}" if employee.minio_image_path else ""
    return {
        "id": employee.id,
        "employee_id": str(employee.id),
        "full_name": employee.full_name,
        "email": "",
        "department": "",
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
    upsert_employee_vector(
        employee.id,
        vector,
        {
            "db_id": employee.id,
            "employee_id": str(employee.id),
            "full_name": employee.full_name,
        },
    )
    employee.is_vectorized = True
    employee.updated_at = now_utc()
    db.commit()


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), employee_id: str = Form(...)) -> dict[str, str]:
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
    employee = Employee(
        full_name=payload.full_name,
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
        employee.updated_at = now_utc()
        db.commit()
        print(f"[WARN] Failed to enqueue embedding job for employee {employee.id}: {exc}", flush=True)

    return _employee_to_dict(employee)


@router.get("")
def list_employees(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    employees = db.query(Employee).order_by(Employee.id.desc()).all()
    return [_employee_to_dict(employee) for employee in employees]


@router.put("/{employee_id}")
def update_employee(employee_id: int, payload: EmployeeUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
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
    employee.updated_at = now_utc()
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
    query = db.query(Employee)
    employee = query.filter(Employee.id == int(employee_id)).first() if employee_id.isdigit() else None
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
def extract_embedding(employee_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
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
    employee = None
    if employee_id.isdigit():
        employee = db.query(Employee).filter(Employee.id == int(employee_id)).first()
    if employee is None:
        return []

    rows = (
        db.query(AttendanceLog)
        .filter(AttendanceLog.employee_id == employee.id)
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
