from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.cache import bump_version, get_json, set_json, versioned_key
from app.config import CACHE_LOGS_TTL_SECONDS
from app.db import AttendanceLog, get_db
from app.security import require_admin
from app.storage import object_url


router = APIRouter(prefix="/api/access-logs", tags=["access-logs"], dependencies=[Depends(require_admin)])


def _snapshot_url(log: AttendanceLog) -> str:
    return object_url(log.minio_snapshot_path) if log.minio_snapshot_path else ""


def _log_to_dict(log: AttendanceLog) -> dict[str, Any]:
    business_id = None
    if log.employee is not None:
        business_id = log.employee.employee_code
    elif log.employee_code:
        business_id = str(log.employee_code)
    return {
        "id": log.id,
        "employee_name": log.employee.full_name if log.employee else None,
        "employee_id": business_id,
        "camera_location": "N/A",
        "timestamp": log.scan_time,
        "status": "allowed" if log.status == "SUCCESS" else "denied",
        "confidence": 0.0,
        "image_url": _snapshot_url(log),
    }


@router.get("")
def list_logs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    cache_key = versioned_key("access_logs", "list")
    cached = get_json(cache_key)
    if isinstance(cached, list):
        return cached
    rows = db.query(AttendanceLog).order_by(AttendanceLog.scan_time.desc()).limit(200).all()
    result = [_log_to_dict(row) for row in rows]
    set_json(cache_key, result, ttl_seconds=CACHE_LOGS_TTL_SECONDS)
    return result


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    cache_key = versioned_key("access_logs", "alerts")
    cached = get_json(cache_key)
    if isinstance(cached, list):
        return cached
    rows = (
        db.query(AttendanceLog)
        .filter(AttendanceLog.status == "STRANGER")
        .filter(AttendanceLog.handled.is_(False))
        .order_by(AttendanceLog.scan_time.desc())
        .limit(50)
        .all()
    )
    result = [
        {
            "id": row.id,
            "timestamp": row.scan_time,
            "camera_location": "N/A",
            "confidence": 0.0,
            "image_url": _snapshot_url(row),
        }
        for row in rows
    ]
    set_json(cache_key, result, ttl_seconds=CACHE_LOGS_TTL_SECONDS)
    return result


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    row = db.query(AttendanceLog).filter(AttendanceLog.id == alert_id).first()
    if row is None:
        return {"status": "ok"}
    row.handled = True
    db.commit()
    bump_version("access_logs")
    return {"status": "ok"}
