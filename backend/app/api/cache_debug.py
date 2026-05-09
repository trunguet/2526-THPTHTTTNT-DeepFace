from __future__ import annotations

from fastapi import APIRouter, Depends

from app.cache import cache_stats, get_version
from app.security import require_admin


router = APIRouter(prefix="/api/cache", tags=["cache"], dependencies=[Depends(require_admin)])


@router.get("/stats")
def cache_debug_stats() -> dict:
    payload: dict = cache_stats()
    payload["versions"] = {
        "employees": get_version("employees"),
        "access_logs": get_version("access_logs"),
    }

    # Best-effort: include some live Redis keys + TTLs (limited).
    try:
        from app.cache import _redis_client  # type: ignore

        if _redis_client is not None:
            keys: list[dict] = []
            patterns = ["cache:employees:*", "cache:access_logs:*"]
            for pattern in patterns:
                for idx, key in enumerate(_redis_client.scan_iter(match=pattern, count=200)):
                    if idx >= 25:
                        break
                    keys.append({"key": key, "ttl": int(_redis_client.ttl(key))})
            payload["redis_keys"] = keys
    except Exception:
        pass

    return payload

