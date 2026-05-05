import os
import uuid
from typing import Any, Dict, Optional

import cv2
from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.utils.db import get_connection

from models.extraction.arcface_wrapper import get_arcface_extractor


try:
	from qdrant_client import QdrantClient
	from qdrant_client.http import models as qdrant_models
except Exception as exc:  # pragma: no cover - optional dependency
	QdrantClient = None
	qdrant_models = None
	_QDRANT_IMPORT_ERROR = exc


router = APIRouter(prefix="/api/employees", tags=["employees"])

UPLOAD_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "uploads"))
os.makedirs(UPLOAD_DIR, exist_ok=True)


class EmployeeCreate(BaseModel):
	full_name: str
	employee_id: Optional[str] = None
	email: Optional[str] = None
	department: Optional[str] = None
	image_url: Optional[str] = None


class EmbeddingRequest(BaseModel):
	image_url: Optional[str] = None


def _resolve_upload_path(image_url: str) -> str:
	if image_url.startswith("/uploads/"):
		return os.path.join(UPLOAD_DIR, image_url.replace("/uploads/", ""))
	if image_url.startswith("http://") or image_url.startswith("https://"):
		raise HTTPException(status_code=400, detail="Remote image URLs are not supported")
	return image_url


def _get_qdrant_client() -> QdrantClient:
	if QdrantClient is None:
		raise RuntimeError(f"qdrant-client import failed: {_QDRANT_IMPORT_ERROR}")

	host = os.getenv("QDRANT_HOST", "localhost")
	port = int(os.getenv("QDRANT_PORT", "6333"))
	return QdrantClient(host=host, port=port)


def _ensure_collection(client: QdrantClient, collection: str) -> None:
	try:
		client.get_collection(collection_name=collection)
	except Exception:
		client.create_collection(
			collection_name=collection,
			vectors_config=qdrant_models.VectorParams(size=512, distance=qdrant_models.Distance.COSINE),
		)


@router.post("/upload-image")
async def upload_image(file: UploadFile = File(...), employee_id: str = Form(...)) -> Dict[str, Any]:
	ext = os.path.splitext(file.filename)[1] or ".jpg"
	filename = f"{employee_id}_{uuid.uuid4().hex}{ext}"
	target_path = os.path.join(UPLOAD_DIR, filename)

	content = await file.read()
	with open(target_path, "wb") as output:
		output.write(content)

	return {"image_url": f"/uploads/{filename}"}


@router.post("")
def create_employee(payload: EmployeeCreate) -> Dict[str, Any]:
	conn = get_connection()
	with conn.cursor() as cursor:
		sql = (
			"INSERT INTO employees (full_name, employee_code, email, department, minio_image_path, is_vectorized) "
			"VALUES (%s, %s, %s, %s, %s, %s)"
		)
		cursor.execute(
			sql,
			(
				payload.full_name,
				payload.employee_id,
				payload.email,
				payload.department,
				payload.image_url,
				False,
			),
		)
		employee_id = cursor.lastrowid

	return {
		"id": employee_id,
		"full_name": payload.full_name,
		"employee_id": payload.employee_id,
		"email": payload.email,
		"department": payload.department,
		"image_url": payload.image_url,
	}


@router.get("")
def list_employees() -> Any:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute(
			"SELECT id, full_name, employee_code, email, department, minio_image_path, created_at "
			"FROM employees ORDER BY id DESC"
		)
		rows = cursor.fetchall()

	for row in rows:
		row["employee_id"] = row.pop("employee_code", None)
		row["image_url"] = row.pop("minio_image_path", None)
	return rows


@router.delete("/{employee_id}")
def delete_employee(employee_id: int) -> Dict[str, Any]:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))

	return {"status": "ok"}


@router.post("/{employee_id}/extract-embedding")
def extract_embedding(employee_id: int, payload: EmbeddingRequest) -> Dict[str, Any]:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute(
			"SELECT full_name, employee_code, minio_image_path FROM employees WHERE id = %s",
			(employee_id,),
		)
		employee = cursor.fetchone()

	if not employee:
		raise HTTPException(status_code=404, detail="Employee not found")

	image_url = payload.image_url or employee.get("minio_image_path")
	if not image_url:
		raise HTTPException(status_code=400, detail="Missing image_url")

	image_path = _resolve_upload_path(image_url)
	image = cv2.imread(image_path)
	if image is None:
		raise HTTPException(status_code=400, detail="Failed to read image file")

	extractor = get_arcface_extractor()
	embedding = extractor.extract_embedding(image)

	collection = os.getenv("QDRANT_COLLECTION", "face_embeddings")
	client = _get_qdrant_client()
	_ensure_collection(client, collection)

	payload_data = {
		"employee_id": str(employee_id),
		"employee_code": employee.get("employee_code"),
		"full_name": employee.get("full_name"),
	}

	client.upsert(
		collection_name=collection,
		points=[
			qdrant_models.PointStruct(
				id=employee_id,
				vector=embedding.tolist(),
				payload=payload_data,
			)
		],
	)

	with conn.cursor() as cursor:
		cursor.execute(
			"UPDATE employees SET is_vectorized = %s, minio_image_path = %s WHERE id = %s",
			(True, image_url, employee_id),
		)

	return {"status": "ok"}


@router.get("/{employee_id}/access-history")
def access_history(employee_id: int) -> Any:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute(
			"SELECT scan_time, status, camera_id FROM attendance_logs "
			"WHERE employee_id = %s ORDER BY scan_time DESC",
			(employee_id,),
		)
		rows = cursor.fetchall()

	history = []
	for row in rows:
		status = row.get("status")
		history.append(
			{
				"timestamp": row.get("scan_time"),
				"access_type": "check_in",
				"status": "allowed" if status == "SUCCESS" else "denied",
				"camera_location": row.get("camera_id"),
			}
		)
	return history
