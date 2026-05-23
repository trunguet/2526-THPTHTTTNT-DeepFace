import json
from dataclasses import asdict, dataclass
from typing import Literal
from uuid import uuid4

from app.config.redis import get_redis_client


ACCESS_QUEUE_NAME = "access_jobs"


@dataclass(frozen=True)
class AccessJob:
    job_id: str
    type: Literal["access_check"]
    log_id: int
    camera_id: int
    image_path: str
    image_key: str | None = None

    def to_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["image_key"] = self.image_key or self.image_path
        return payload


def build_access_job(log_id: int, camera_id: int, image_key: str) -> AccessJob:
    return AccessJob(
        job_id=str(uuid4()),
        type="access_check",
        log_id=log_id,
        camera_id=camera_id,
        image_path=image_key,
        image_key=image_key,
    )


def enqueue_access_job(log_id: int, camera_id: int, image_key: str) -> AccessJob:
    job = build_access_job(log_id, camera_id, image_key)
    redis_client = get_redis_client()
    redis_client.rpush(ACCESS_QUEUE_NAME, json.dumps(job.to_payload()))
    return job
