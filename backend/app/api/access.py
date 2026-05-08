from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import decode_base64_image, validate_image, verify_liveness_and_embedding
from app.db import AttendanceLog, Employee, get_db
from app.schemas import VerifyFaceRequest
from app.storage import save_bytes


router = APIRouter(prefix="/api/access", tags=["access"])


def _resolve_employee(db: Session, identifier: str | None) -> Employee | None:
    value = str(identifier or "").strip()
    if not value:
        return None

    employee = db.query(Employee).filter(Employee.employee_code == value).first()
    if employee is not None:
        return employee

    if value.isdigit():
        return db.query(Employee).filter(Employee.id == int(value)).first()
    return None


@router.post("/verify-face")
def verify_face(request: VerifyFaceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        image_bytes = decode_base64_image(request.image)
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    # Optional hint from client (used to link failed attempts to a known employee).
    # If the provided identifier does not exist, ignore it so face verification
    # still works (the client might be in demo mode or misconfigured).
    employee_hint = _resolve_employee(db, request.employee_id)

    snapshot_key, snapshot_url = save_bytes("audit/unknown", image_bytes)
    try:
        result = verify_liveness_and_embedding(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face pipeline failed: {exc}")

    match = result.match
    score = match.score if match else 0.0
    payload = match.payload if match else {}

    if result.status == "accepted" and match is not None:
        matched_code = str(match.employee_id or "").strip() or None
        employee = _resolve_employee(db, matched_code)
        db_id = payload.get("db_id")
        if db_id is None:
            # Backward/compat: some vector payloads may store the business id only.
            db_id = payload.get("id") or payload.get("employee_db_id")
        if db_id is not None:
            try:
                employee = db.query(Employee).filter(Employee.id == int(db_id)).first()
            except (TypeError, ValueError):
                employee = None

        if employee is None:
            business_id = payload.get("employee_id") or payload.get("employee_code")
            if business_id:
                employee = _resolve_employee(db, str(business_id))

        # If we cannot resolve the matched employee but the client provided an employee hint,
        # still link the log row so "seen today" reflects the successful scan.
        if employee is None and employee_hint is not None:
            employee = employee_hint

        log = AttendanceLog(
            employee_code=(matched_code or (employee.employee_code if employee else None)),
            status="SUCCESS",
            minio_snapshot_path=snapshot_key,
        )
        db.add(log)
        db.commit()

        return {
            "status": "allowed",
            "employee_id": (matched_code or (employee.employee_code if employee else None)),
            "employee_name": employee.full_name if employee else str(payload.get("full_name") or ""),
            "confidence": score,
            "audit_object": snapshot_key,
            "image_url": snapshot_url,
            "reason": result.reason,
        }

    linked_employee = employee_hint
    log_status = (
        "FAILED"
        if linked_employee is not None
        else ("STRANGER" if result.reason == "no_match" else "FAILED")
    )
    log = AttendanceLog(
        employee_code=linked_employee.employee_code if linked_employee else None,
        status=log_status,
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
        "status": "denied"
        if linked_employee is not None
        else ("stranger" if result.reason == "no_match" else "denied"),
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
