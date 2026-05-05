import json

import redis

from app.config import REDIS_URL

QUEUE_NAME = "embedding_jobs"


def get_redis_client() -> redis.Redis:
    return redis.from_url(REDIS_URL, decode_responses=True)


def enqueue_embedding_job(employee_id: int) -> None:
    client = get_redis_client()
    client.rpush(QUEUE_NAME, json.dumps({"type": "extract_embedding", "employee_id": employee_id}))
