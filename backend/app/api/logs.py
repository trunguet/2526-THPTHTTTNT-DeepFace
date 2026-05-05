from typing import Any, Dict, List

from fastapi import APIRouter

from backend.app.utils.db import get_connection


router = APIRouter(prefix="/api/access-logs", tags=["access-logs"])


@router.get("")
def list_logs() -> List[Dict[str, Any]]:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute(
			"SELECT a.id, a.employee_id, a.scan_time, a.status, a.camera_id, a.similarity, "
			"e.full_name, e.employee_code "
			"FROM attendance_logs a "
			"LEFT JOIN employees e ON a.employee_id = e.id "
			"ORDER BY a.scan_time DESC LIMIT 200"
		)
		rows = cursor.fetchall()

	logs = []
	for row in rows:
		status = row.get("status")
		logs.append(
			{
				"id": row.get("id"),
				"employee_name": row.get("full_name"),
				"employee_id": row.get("employee_code"),
				"camera_location": row.get("camera_id"),
				"timestamp": row.get("scan_time"),
				"status": "allowed" if status == "SUCCESS" else "denied",
			}
		)

	return logs


@router.get("/alerts")
def list_alerts() -> List[Dict[str, Any]]:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute(
			"SELECT id, scan_time, camera_id, similarity, minio_snapshot_path "
			"FROM attendance_logs WHERE status = 'STRANGER' AND handled = 0 "
			"ORDER BY scan_time DESC LIMIT 50"
		)
		rows = cursor.fetchall()

	alerts = []
	for row in rows:
		alerts.append(
			{
				"id": row.get("id"),
				"timestamp": row.get("scan_time"),
				"camera_location": row.get("camera_id"),
				"confidence": float(row.get("similarity") or 0.0),
				"image_url": row.get("minio_snapshot_path"),
			}
		)
	return alerts


@router.post("/alerts/{alert_id}/dismiss")
def dismiss_alert(alert_id: int) -> Dict[str, Any]:
	conn = get_connection()
	with conn.cursor() as cursor:
		cursor.execute("UPDATE attendance_logs SET handled = 1 WHERE id = %s", (alert_id,))
	return {"status": "ok"}
