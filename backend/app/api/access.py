from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import decode_base64_image, validate_image, verify_liveness_and_embedding
from app.db import AttendanceLog, Employee, get_db
from app.schemas import VerifyFaceRequest
from app.storage import save_bytes


router = APIRouter(prefix="/api/access", tags=["access"])


@router.post("/verify-face")
def verify_face(request: VerifyFaceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        image_bytes = decode_base64_image(request.image)
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    snapshot_key, snapshot_url = save_bytes("audit/unknown", image_bytes)
    try:
        result = verify_liveness_and_embedding(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face pipeline failed: {exc}")

    match = result.match
    score = match.score if match else 0.0
    payload = match.payload if match else {}

    if result.status == "accepted" and match is not None:
        employee = None
        db_id = payload.get("db_id")
        if db_id is not None:
            employee = db.query(Employee).filter(Employee.id == int(db_id)).first()

        log = AttendanceLog(
            employee_id=employee.id if employee else None,
            status="SUCCESS",
            minio_snapshot_path=snapshot_key,
        )
        db.add(log)
        db.commit()

        return {
            "status": "allowed",
            "employee_id": (employee.employee_code or str(employee.id)) if employee else None,
            "employee_name": employee.full_name if employee else str(payload.get("full_name") or ""),
            "confidence": score,
            "audit_object": snapshot_key,
            "image_url": snapshot_url,
            "reason": result.reason,
        }

    log = AttendanceLog(
        employee_id=None,
        status="STRANGER" if result.reason == "no_match" else "FAILED",
        minio_snapshot_path=snapshot_key,
    )
    db.add(log)
    db.commit()
    message = {
        "spoof": "Kiểm tra chống giả mạo thất bại",
        "no_face": "Không phát hiện khuôn mặt",
        "no_match": "Khuôn mặt không khớp với bất kỳ nhân viên nào",
        "multiple_faces": "Phát hiện nhiều hơn một khuôn mặt. Vui lòng chỉ để một người trước camera.",
    }.get(result.reason, "Xác thực khuôn mặt thất bại")

    return {
        "status": "stranger" if result.reason == "no_match" else "denied",
        "reason": result.reason,
        "message": message,
        "confidence": score,
        "audit_object": snapshot_key,
        "image_url": snapshot_url,
        "anti_spoof": {
            "real_score": result.anti_spoof.real_score,
            "spoof_score": result.anti_spoof.spoof_score,
            "confidence": result.anti_spoof.confidence,
        }
        if result.anti_spoof
        else None,
    }
