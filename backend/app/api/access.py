from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.ai import build_embedding, decode_base64_image, qdrant_score, validate_image
from app.config import MATCH_THRESHOLD
from app.db import AttendanceLog, Employee, get_db
from app.schemas import VerifyFaceRequest
from app.storage import save_bytes
from app.vector_store import search_face


router = APIRouter(prefix="/api/access", tags=["access"])


def _top_payload(result: Any) -> dict[str, Any]:
    payload = getattr(result, "payload", None)
    return payload if isinstance(payload, dict) else {}


@router.post("/verify-face")
def verify_face(request: VerifyFaceRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        image_bytes = decode_base64_image(request.image)
        validate_image(image_bytes)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Invalid image: {exc}")

    snapshot_key, snapshot_url = save_bytes("audit/unknown", image_bytes)
    vector = build_embedding(image_bytes)

    results = search_face(vector, limit=1)
    top = results[0] if results else None
    score = qdrant_score(top) if top else 0.0
    payload = _top_payload(top)

    if top is not None and score >= MATCH_THRESHOLD:
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
            "employee_id": str(employee.id) if employee else None,
            "employee_name": employee.full_name if employee else str(payload.get("full_name") or ""),
            "confidence": score,
            "audit_object": snapshot_key,
            "image_url": snapshot_url,
        }

    log = AttendanceLog(
        employee_id=None,
        status="STRANGER",
        minio_snapshot_path=snapshot_key,
    )
    db.add(log)
    db.commit()

    return {
        "status": "stranger",
        "confidence": score,
        "audit_object": snapshot_key,
        "image_url": snapshot_url,
    }
