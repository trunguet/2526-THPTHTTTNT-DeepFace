import json
import logging
import time
from collections.abc import Callable
from typing import Any

from app.config.redis import get_redis_client
from app.tasks.access_job import handle_access_job
from app.tasks.embedding_job import handle_embedding_job


ACCESS_QUEUE_NAME = "access_jobs"
EMBEDDING_QUEUE_NAME = "embedding_jobs"
QUEUE_NAMES = [EMBEDDING_QUEUE_NAME, ACCESS_QUEUE_NAME]


def process_job(queue_name: str, payload: dict[str, Any]) -> None:
    if queue_name == EMBEDDING_QUEUE_NAME:
        handle_embedding_job(payload)
        return

    if queue_name == ACCESS_QUEUE_NAME:
        handle_access_job(payload)
        return

    raise ValueError(f"Unsupported queue: {queue_name}")


def process_next_job(timeout_seconds: int = 5) -> bool:
    redis_client = get_redis_client()
    queued_item = redis_client.blpop(QUEUE_NAMES, timeout=timeout_seconds)

    if queued_item is None:
        return False

    queue_name, raw_payload = queued_item
    try:
        payload = json.loads(raw_payload)
        process_job(queue_name, payload)
    except Exception:
        logging.exception(
            "Failed to process job from queue=%s payload=%s",
            queue_name,
            raw_payload,
        )
    return True


def run_queue_worker(should_continue: Callable[[], bool]) -> None:
    logging.info("Queue worker listening on queues: %s", ", ".join(QUEUE_NAMES))

    while should_continue():
        try:
            process_next_job()
        except Exception:
            logging.exception("Queue worker failed while processing a job")
            time.sleep(5)
