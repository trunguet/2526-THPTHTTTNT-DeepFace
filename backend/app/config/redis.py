from redis import Redis
from redis.exceptions import RedisError

from app.core.config import settings


def get_redis_client() -> Redis:
    return Redis.from_url(settings.redis_url, decode_responses=True)


def check_redis_connection() -> tuple[bool, str | None]:
    try:
        get_redis_client().ping()
    except RedisError as exc:
        return False, exc.__class__.__name__

    return True, None
