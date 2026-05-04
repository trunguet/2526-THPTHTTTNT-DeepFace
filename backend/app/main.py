from datetime import datetime, timezone

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.ai import build_embedding, decode_base64_image, qdrant_score, validate_image
from app.config import MATCH_THRESHOLD
from app.db import AccessLog, Employee, get_db, init_db, now_utc
from app.jobs import enqueue_embedding_job
from app.schemas import EmployeeCreate, EmployeeUpdate, LoginRequest, VerifyFaceRequest
from app.storage import delete_object, init_bucket, read_bytes, save_bytes
from app.vector_store import delete_employee_vector, init_collection, search_face


app = FastAPI(title="DeepFace API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def employee_to_dict(employee: Employee) -> dict:
    return {
        "id": employee.id,
        "employee_id": employee.employee_id,
        "full_name": employee.full_name,
        "email": employee.email,
        "department": employee.department,
        "image_url": employee.image_url,
        "image_object_key": employee.image_object_key,
        "embedding_status": employee.embedding_status,
        "created_at": employee.created_at.isoformat() if employee.created_at else None,
    }


def log_to_dict(log: AccessLog) -> dict:
    return {
        "id": log.id,
        "employee_id": log.employee_id,
        "employee_name": log.employee_name,
        "camera_location": log.camera_location,
        "access_type": log.access_type,
        "status": log.status,
        "confidence": log.confidence,
        "image_url": log.image_url,
        "alert_dismissed": log.alert_dismissed,
        "timestamp": log.timestamp.isoformat() if log.timestamp else None,
    }


@app.on_event("startup")
def startup() -> None:
    init_db()
    init_bucket()
    init_collection()


@app.get("/")
async def root() -> dict[str, str]:
    return {"service": "deepface-backend", "status": "running"}


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/auth/login")
async def login(payload: LoginRequest) -> dict:
    role = "admin" if payload.username.lower() == "admin" else "user"
    return {
        "access_token": f"demo-{role}-token",
        "token_type": "bearer",
        "role": role,
        "employee_id": payload.username if role == "user" else "",
        "employee_name": payload.username if role == "user" else "Admin",
    }


@app.get("/api/files/{object_key:path}")
async def get_file(object_key: str) -> Response:
    try:
        content = read_bytes(object_key)
    except Exception as exc:
        raise HTTPException(status_code=404, detail="File not found") from exc
    return Response(content=content, media_type="image/jpeg")


@app.get("/api/employees")
async def list_employees(db: Session = Depends(get_db)) -> list[dict]:
    employees = db.query(Employee).order_by(Employee.created_at.desc()).all()
    return [employee_to_dict(employee) for employee in employees]


@app.post("/api/employees/upload-image")
async def upload_employee_image(
    file: UploadFile = File(...),
    employee_id: str = Form("unknown"),
) -> dict[str, str]:
    image_bytes = await file.read()
    try:
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Uploaded file is not a valid image") from exc

    object_key, image_url = save_bytes(
        f"employees/{employee_id}",
        image_bytes,
        content_type=file.content_type or "image/jpeg",
    )
    return {"image_url": image_url, "url": image_url, "object_key": object_key}


@app.post("/api/employees")
async def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db)) -> dict:
    existing = db.query(Employee).filter(Employee.employee_id == payload.employee_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Employee ID already exists")

    employee = Employee(
        employee_id=payload.employee_id.strip(),
        full_name=payload.full_name.strip(),
        email=str(payload.email or "").strip(),
        department=payload.department.strip(),
        image_url=payload.image_url,
        image_object_key=payload.image_object_key,
        embedding_status="pending" if payload.image_object_key else "missing_image",
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)
    return employee_to_dict(employee)


@app.post("/api/employees/{employee_id}/extract-embedding")
async def extract_embedding(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str | int]:
    employee = find_employee(db, employee_id)
    if not employee.image_object_key:
        raise HTTPException(status_code=400, detail="Employee has no image to index")

    employee.embedding_status = "queued"
    employee.updated_at = now_utc()
    db.commit()
    enqueue_embedding_job(employee.id)
    return {"status": "queued", "employee_id": employee.employee_id, "id": employee.id}


@app.put("/api/employees/{employee_id}")
async def update_employee(
    employee_id: str,
    payload: EmployeeUpdate,
    db: Session = Depends(get_db),
) -> dict:
    employee = find_employee(db, employee_id)
    if payload.full_name is not None:
        employee.full_name = payload.full_name.strip()
    if payload.email is not None:
        employee.email = str(payload.email).strip()
    if payload.department is not None:
        employee.department = payload.department.strip()
    employee.updated_at = now_utc()
    db.commit()
    db.refresh(employee)
    return employee_to_dict(employee)


@app.delete("/api/employees/{employee_id}")
async def delete_employee(employee_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    employee = find_employee(db, employee_id)
    try:
        delete_employee_vector(employee.id)
    except Exception:
        pass
    try:
        delete_object(employee.image_object_key)
    except Exception:
        pass
    db.delete(employee)
    db.commit()
    return {"status": "deleted"}


@app.post("/api/access/verify-face")
async def verify_face(payload: VerifyFaceRequest, db: Session = Depends(get_db)) -> dict:
    try:
        image_bytes = decode_base64_image(payload.image)
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid base64 image") from exc

    snapshot_key, snapshot_url = save_bytes("snapshots", image_bytes)
    vector = build_embedding(image_bytes)

    employees_count = db.query(Employee).filter(Employee.embedding_status == "indexed").count()
    matched_employee: Employee | None = None
    confidence = 0.0

    if employees_count:
        results = search_face(vector, limit=1)
        if results:
            confidence = qdrant_score(results[0])
            payload_id = (results[0].payload or {}).get("db_id")
            if confidence >= MATCH_THRESHOLD and payload_id:
                matched_employee = db.query(Employee).filter(Employee.id == int(payload_id)).first()

    if matched_employee:
        status = "allowed"
        employee_db_id = matched_employee.id
        employee_id = matched_employee.employee_id
        employee_name = matched_employee.full_name
        message = "Face verified successfully"
    else:
        status = "stranger"
        employee_db_id = None
        employee_id = ""
        employee_name = ""
        message = "No matching employee found"

    log = AccessLog(
        employee_db_id=employee_db_id,
        employee_id=employee_id,
        employee_name=employee_name,
        camera_location=payload.camera_location,
        access_type=payload.access_type,
        status=status,
        confidence=confidence,
        snapshot_object_key=snapshot_key,
        image_url=snapshot_url,
        alert_dismissed=False,
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return {
        "status": status,
        "recognized": status == "allowed",
        "employee_id": employee_id,
        "employee_name": employee_name,
        "confidence": confidence,
        "message": message,
        "snapshot_url": snapshot_url,
        "log_id": log.id,
    }


@app.get("/api/access-logs")
async def list_access_logs(db: Session = Depends(get_db)) -> list[dict]:
    logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(200).all()
    return [log_to_dict(log) for log in logs]


@app.get("/api/access-logs/alerts")
async def list_alerts(db: Session = Depends(get_db)) -> list[dict]:
    logs = (
        db.query(AccessLog)
        .filter(AccessLog.status == "stranger", AccessLog.alert_dismissed.is_(False))
        .order_by(AccessLog.timestamp.desc())
        .limit(100)
        .all()
    )
    return [log_to_dict(log) for log in logs]


@app.post("/api/access-logs/alerts/{alert_id}/dismiss")
async def dismiss_alert(alert_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    log = db.query(AccessLog).filter(AccessLog.id == alert_id).first()
    if not log:
        raise HTTPException(status_code=404, detail="Alert not found")
    log.alert_dismissed = True
    db.commit()
    return {"status": "dismissed"}


@app.get("/api/employees/{employee_id}/access-history")
async def employee_access_history(employee_id: str, db: Session = Depends(get_db)) -> list[dict]:
    logs = (
        db.query(AccessLog)
        .filter(AccessLog.employee_id == employee_id)
        .order_by(AccessLog.timestamp.desc())
        .limit(200)
        .all()
    )
    return [log_to_dict(log) for log in logs]


def find_employee(db: Session, employee_id: str) -> Employee:
    filters = [Employee.employee_id == employee_id]
    if employee_id.isdigit():
        filters.append(Employee.id == int(employee_id))
    employee = db.query(Employee).filter(or_(*filters)).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee
