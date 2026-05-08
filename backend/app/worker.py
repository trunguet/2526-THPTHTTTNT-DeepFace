import json
import time

from sqlalchemy.orm import Session

from app.ai import build_embedding
from app.db import Employee, SessionLocal, init_db, now_utc
from app.jobs import QUEUE_NAME, get_redis_client
from app.storage import init_bucket, read_bytes
from app.vector_store import init_collection, upsert_employee_vector


def process_embedding_job(db: Session, employee_id: int) -> None:
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return

    try:
        image_bytes = read_bytes(employee.minio_image_path)
        vector = build_embedding(image_bytes)
        upsert_employee_vector(
            employee.id,
            vector,
            {
                "db_id": employee.id,
                "employee_id": employee.employee_code or str(employee.id),
                "full_name": employee.full_name,
            },
        )
        employee.is_vectorized = True
    except Exception as exc:
        employee.is_vectorized = False
        print(f"Failed to index employee {employee_id}: {exc}", flush=True)
    finally:
        employee.updated_at = now_utc()
        db.commit()


def main() -> None:
    init_db()
    init_bucket()
    init_collection()
    redis_client = get_redis_client()
    print("Embedding worker started", flush=True)

    while True:
        _, raw_job = redis_client.blpop(QUEUE_NAME)
        try:
            job = json.loads(raw_job)
            if job.get("type") == "extract_embedding":
                with SessionLocal() as db:
                    process_embedding_job(db, int(job["employee_id"]))
        except Exception as exc:
            print(f"Worker job failed: {exc}", flush=True)
            time.sleep(1)


if __name__ == "__main__":
    main()
