from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ai import build_embedding, validate_image
from app.cache import bump_version, get_json, set_json, versioned_key
from app.config import CACHE_EMPLOYEES_TTL_SECONDS
from app.db import AttendanceLog, Employee, EmployeeBackup, get_db
from app.employee_lookup import resolve_employee
from app.jobs import enqueue_embedding_job
from app.schemas import EmployeeCreate, EmployeeUpdate
from app.security import require_admin
from app.storage import delete_object, read_bytes, save_bytes
from app.vector_store import delete_employee_vector, init_collection, upsert_employee_vector


router = APIRouter(prefix="/api/employees", tags=["employees"])


def _warn(message: str, exc: Exception) -> None:
    print(f"[WARN] {message}: {exc}", flush=True)


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


def _enqueue_embedding(employee_id: int) -> bool:
    try:
        enqueue_embedding_job(employee_id)
        return True
    except Exception as exc:
        _warn(f"Failed to enqueue embedding job for employee {employee_id}", exc)
        return False


@router.post("/upload-image", dependencies=[Depends(require_admin)])
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
    bump_version("employees")
    return {"image_url": image_url, "image_object_key": object_key}


@router.post("", dependencies=[Depends(require_admin)])
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
    _enqueue_embedding(employee.id)

    bump_version("employees")
    return _employee_to_dict(employee)


@router.get("", dependencies=[Depends(require_admin)])
def list_employees(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    cache_key = versioned_key("employees", "list")
    cached = get_json(cache_key)
    if isinstance(cached, list):
        return cached
    employees = db.query(Employee).order_by(Employee.id.desc()).all()
    result = [_employee_to_dict(employee) for employee in employees]
    set_json(cache_key, result, ttl_seconds=CACHE_EMPLOYEES_TTL_SECONDS)
    return result


@router.get("/unscanned-today", dependencies=[Depends(require_admin)])
def list_unscanned_today(db: Session = Depends(get_db)) -> dict[str, Any]:
    cache_key = versioned_key("employees", "unscanned_today")
    cached = get_json(cache_key)
    if isinstance(cached, dict) and "items" in cached:
        return cached
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
    result = {
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
    set_json(cache_key, result, ttl_seconds=CACHE_EMPLOYEES_TTL_SECONDS)
    return result


@router.get("/lookup/{employee_id}")
def lookup_employee(employee_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Public lightweight lookup used by the User UI before scanning.

    It avoids the old demo-only login flow while keeping the actual verification
    decision inside the face-recognition pipeline.
    """
    employee = resolve_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    return {
        "employee_id": employee.employee_code,
        "full_name": employee.full_name,
        "department": employee.department or "",
    }


@router.post("/reindex-all", dependencies=[Depends(require_admin)])
def reindex_all(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Enqueue embedding extraction for every employee.

    Use this when recognition matches are incorrect due to stale embeddings/payloads in Qdrant.
    """
    employees = db.query(Employee).order_by(Employee.id.asc()).all()
    queued = 0
    skipped = 0
    for employee in employees:
        if not employee.minio_image_path:
            skipped += 1
            continue
        if _enqueue_embedding(employee.id):
            queued += 1
            continue
        skipped += 1

    bump_version("employees")
    return {"status": "ok", "queued": queued, "skipped": skipped, "total": len(employees)}


@router.post("/qdrant/reset", dependencies=[Depends(require_admin)])
def reset_qdrant_and_reindex(db: Session = Depends(get_db)) -> dict[str, Any]:
    """
    Hard reset Qdrant collection and reindex all employees.

    This removes old/test vectors that can cause matches returning wrong employee_code (e.g. '1').
    """
    from app.config import QDRANT_COLLECTION
    from app.vector_store import get_qdrant_client

    client = get_qdrant_client()
    try:
        client.delete_collection(collection_name=QDRANT_COLLECTION)
    except Exception as exc:
        _warn("Failed to delete Qdrant collection", exc)

    init_collection()
    result = reindex_all(db)
    bump_version("employees")
    return {"status": "ok", "collection": QDRANT_COLLECTION, **result}


@router.put("/{employee_id}", dependencies=[Depends(require_admin)])
def update_employee(employee_id: str, payload: EmployeeUpdate, db: Session = Depends(get_db)) -> dict[str, Any]:
    employee = resolve_employee(db, employee_id)
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
            _warn(f"Failed to refresh Qdrant payload for employee {employee.id}", exc)

    bump_version("employees")
    return _employee_to_dict(employee)


@router.delete("/{employee_id}", dependencies=[Depends(require_admin)])
def delete_employee(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = resolve_employee(db, employee_id)
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
        _warn(f"Failed to delete Qdrant vector for employee {vector_id}", exc)
    try:
        delete_object(object_key)
    except Exception as exc:
        _warn(f"Failed to delete employee image {object_key}", exc)

    bump_version("employees")
    return {"status": "ok"}


@router.post("/{employee_id}/extract-embedding", dependencies=[Depends(require_admin)])
def extract_embedding(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = resolve_employee(db, employee_id)
    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found")

    try:
        _index_employee(employee, db)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Embedding extraction failed: {exc}")
    bump_version("employees")
    return {"status": "ok"}


@router.get("/{employee_id}/access-history")
def access_history(employee_id: str, db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    employee = resolve_employee(db, employee_id)
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
