from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import decode_base64_image, validate_image, verify_liveness_and_embedding
from app.db import AttendanceLog, Employee, get_db
from app.employee_lookup import resolve_employee
from app.schemas import VerifyFaceRequest
from app.storage import save_bytes
from app.cache import bump_version


router = APIRouter(prefix="/api/access", tags=["access"])


def _attendance_log(employee: Employee | None, status: str, snapshot_key: str) -> AttendanceLog:
    return AttendanceLog(
        employee_id=employee.id if employee else None,
        employee_code=employee.employee_code if employee else None,
        status=status,
        minio_snapshot_path=snapshot_key,
    )


@router.post("/verify-face")
def verify_face(request: VerifyFaceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        image_bytes = decode_base64_image(request.image)
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    # Optional hint from client (used to link failed attempts to a known employee).
    # If the provided identifier does not exist, ignore it so face verification
    # still works even when the client is misconfigured.
    employee_hint = resolve_employee(db, request.employee_id)

    snapshot_key, snapshot_url = save_bytes("audit/unknown", image_bytes)

    # Optional liveness challenge gate (computed client-side).
    # If the client provides a failed result, reject immediately.
    if request.challenge_passed is False:
        linked_employee = employee_hint
        log = _attendance_log(linked_employee, "FAILED", snapshot_key)
        db.add(log)
        db.commit()
        bump_version("access_logs")
        return {
            "status": "denied",
            "reason": "challenge_failed",
            "message": "Không qua challenge chống giả mạo (chớp mắt/quay đầu).",
            "confidence": 0.0,
            "audit_object": snapshot_key,
            "image_url": snapshot_url,
            "challenge": {
                "type": request.challenge_type,
                "passed": False,
            },
        }
    try:
        result = verify_liveness_and_embedding(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Face pipeline failed: {exc}")

    match = result.match
    score = match.score if match else 0.0
    payload = match.payload if match else {}

    if result.status == "accepted" and match is not None:
        matched_code = str(match.employee_id or "").strip() or None
        employee = resolve_employee(db, matched_code)
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
                employee = resolve_employee(db, business_id)

        # IMPORTANT:
        # - attendance_logs.employee_code must always equal employees.employee_code (business key).
        # - If the match cannot be resolved to an employee row, treat it as STRANGER.
        #   This usually happens when Qdrant still contains stale/test vectors (e.g. payload.employee_id = "1").
        if employee is None:
            log = _attendance_log(None, "STRANGER", snapshot_key)
            db.add(log)
            db.commit()
            bump_version("access_logs")
            return {
                "status": "stranger",
                "reason": "unknown_employee",
                "message": "Embedding match nhưng không tìm thấy nhân viên trong CSDL. Vui lòng cleanup/reindex embeddings.",
                "confidence": score,
                "audit_object": snapshot_key,
                "image_url": snapshot_url,
            }

        log = _attendance_log(employee, "SUCCESS", snapshot_key)
        db.add(log)
        db.commit()
        bump_version("access_logs")

        return {
            "status": "allowed",
            "employee_id": employee.employee_code,
            "employee_name": employee.full_name,
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
    log = _attendance_log(linked_employee, log_status, snapshot_key)
    db.add(log)
    db.commit()
    bump_version("access_logs")
    message = {
        "spoof": "Kiểm tra chống giả mạo thất bại",
        "minifas_low_score": "MiniFAS score thấp, vui lòng thử lại",
        "no_face": "Không phát hiện khuôn mặt",
        "no_match": "Khuôn mặt không khớp với bất kỳ nhân viên nào",
        "multiple_faces": "Phát hiện nhiều hơn một khuôn mặt. Vui lòng chỉ để một người trước camera.",
        "too_dark": "Khung hình quá tối. Vui lòng tăng ánh sáng và thử lại.",
        "face_too_close": "Khuôn mặt quá sát camera. Vui lòng lùi xa hơn và thử lại.",
        "face_too_far": "Khuôn mặt quá xa camera. Vui lòng lại gần hơn và thử lại.",
        "face_bright_bg_dark": "Mặt sáng bất thường nhưng nền tối. Vui lòng điều chỉnh ánh sáng và thử lại.",
        "face_tilted": "Khuôn mặt bị nghiêng. Vui lòng giữ thẳng mặt và thử lại.",
        "too_blurry": "Hình ảnh bị mờ/rung. Vui lòng giữ yên và thử lại.",
        "face_turned": "Khuôn mặt đang quay sang trái/phải hoặc ngước/cúi quá nhiều. Vui lòng nhìn thẳng camera và thử lại.",
        "challenge_failed": "Không qua challenge chống giả mạo (chớp mắt/quay đầu).",
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
