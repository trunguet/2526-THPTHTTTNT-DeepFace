from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db import AttendanceLog, get_db
from app.storage import object_url


router = APIRouter(prefix="/api/access-logs", tags=["access-logs"])


def _snapshot_url(log: AttendanceLog) -> str:
    return object_url(log.minio_snapshot_path) if log.minio_snapshot_path else ""


def _log_to_dict(log: AttendanceLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "employee_name": log.employee.full_name if log.employee else None,
        "employee_id": str(log.employee_id) if log.employee_id else None,
        "camera_location": "N/A",
        "timestamp": log.scan_time,
        "status": "allowed" if log.status == "SUCCESS" else "denied",
        "confidence": 0.0,
        "image_url": _snapshot_url(log),
    }


@router.get("")
def list_logs(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = db.query(AttendanceLog).order_by(AttendanceLog.scan_time.desc()).limit(200).all()
    return [_log_to_dict(row) for row in rows]


@router.get("/alerts")
def list_alerts(db: Session = Depends(get_db)) -> list[dict[str, Any]]:
    rows = (
        db.query(AttendanceLog)
        .filter(AttendanceLog.status == "STRANGER")
        .order_by(AttendanceLog.scan_time.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": row.id,
            "timestamp": row.scan_time,
            "camera_location": "N/A",
            "confidence": 0.0,
            "image_url": _snapshot_url(row),
        }
        for row in rows
    ]


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)) -> dict[str, str]:
    # The required attendance_logs schema has no handled/dismissed column.
    # Keep this endpoint as a UI acknowledgement without mutating the log schema.
    return {"status": "ok"}
