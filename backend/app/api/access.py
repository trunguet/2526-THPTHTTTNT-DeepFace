import base64
import os
import sys
from typing import Any, Dict, Optional, Tuple

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel


PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from worker.tasks.pipeline import build_default_components, run_pipeline

router = APIRouter(prefix="/api/access", tags=["access"])


class VerifyFaceRequest(BaseModel):
	image: str
	camera_id: Optional[str] = None
	client_id: Optional[str] = None


_components = None


def _get_components():
	global _components
	if _components is None:
		_components = build_default_components()
	return _components


def _decode_image(data_url: str) -> bytes:
	if "," in data_url:
		_, payload = data_url.split(",", 1)
	else:
		payload = data_url

	try:
		return base64.b64decode(payload)
	except Exception as exc:
		raise HTTPException(status_code=400, detail=f"Invalid base64 image: {exc}")


def _extract_employee_name(payload: Optional[Dict[str, Any]]) -> Optional[str]:
	if not payload:
		return None
	for key in ("full_name", "employee_name", "name"):
		if key in payload:
			return str(payload[key])
	return None


@router.post("/verify-face")
def verify_face(request: VerifyFaceRequest):
	detector, anti_spoof, embedder, matcher, storage = _get_components()

	image_bytes = _decode_image(request.image)

	camera_id = request.camera_id or "unknown"
	client_id = request.client_id or "unknown"

	result = run_pipeline(
		frame=image_bytes,
		camera_id=camera_id,
		client_id=client_id,
		detector=detector,
		anti_spoof=anti_spoof,
		embedder=embedder,
		matcher=matcher,
		storage=storage,
	)

	if result.status == "accepted":
		return {
			"status": "allowed",
			"employee_id": result.employee_id,
			"employee_name": _extract_employee_name(result.payload),
			"confidence": float(result.similarity or 0.0),
			"audit_object": result.audit_object,
		}

	if result.reason == "no_match":
		return {
			"status": "stranger",
			"confidence": float(result.similarity or 0.0),
			"audit_object": result.audit_object,
		}

	message = "Face verification failed"
	if result.reason == "spoof":
		message = "Spoof detected"
	elif result.reason == "no_face":
		message = "No face detected"

	return {
		"status": "denied",
		"message": message,
		"audit_object": result.audit_object,
	}
