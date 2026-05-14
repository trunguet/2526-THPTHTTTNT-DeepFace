from __future__ import annotations

from fastapi import APIRouter, Depends

from app.cache import cache_stats, get_version, redis_key_ttls
from app.security import require_admin


router = APIRouter(prefix="/api/cache", tags=["cache"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def cache_debug_stats() -> dict:
    payload: dict = cache_stats()
    payload["versions"] = {
        "employees": get_version("employees"),
        "access_logs": get_version("access_logs"),
    }

    patterns = ["cache:employees:*", "cache:access_logs:*"]
    payload["redis_keys"] = redis_key_ttls(patterns)

    return payload
