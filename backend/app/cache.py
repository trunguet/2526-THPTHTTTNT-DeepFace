from __future__ import annotations

import json
import threading
import time
from collections import OrderedDict
from typing import Any

import redis
from fastapi.encoders import jsonable_encoder

from app.config import (
    CACHE_L1_MAX_ENTRIES,
    CACHE_REDIS_ENABLED,
    REDIS_URL,
)


class InMemoryTTLCache:
    def __init__(self, *, max_entries: int = 512):
        self._max_entries = max(16, int(max_entries))
        self._lock = threading.Lock()
        self._data: OrderedDict[str, tuple[float, Any]] = OrderedDict()

    def get(self, key: str) -> Any | None:
        now = time.time()
        with self._lock:
            item = self._data.get(key)
            if item is None:
                return None
            exp, value = item
            if exp < now:
                self._data.pop(key, None)
                return None
            self._data.move_to_end(key)
            return value

    def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        now = time.time()
        exp = now + max(1, int(ttl_seconds))
        with self._lock:
            self._data[key] = (exp, value)
            self._data.move_to_end(key)
            while len(self._data) > self._max_entries:
                self._data.popitem(last=False)

    def delete(self, key: str) -> None:
        with self._lock:
            self._data.pop(key, None)


_l1 = InMemoryTTLCache(max_entries=CACHE_L1_MAX_ENTRIES)
_versions_l1: dict[str, int] = {}
_stats_lock = threading.Lock()
_stats: dict[str, int] = {
    "l1_hit": 0,
    "l1_miss": 0,
    "redis_hit": 0,
    "redis_miss": 0,
    "set_ok": 0,
    "set_err": 0,
}


def _get_redis() -> redis.Redis | None:
    if not CACHE_REDIS_ENABLED:
        return None
    try:
        return redis.from_url(REDIS_URL, decode_responses=True)
    except Exception:
        return None


_redis_client: redis.Redis | None = _get_redis()


def get_json(key: str) -> Any | None:
    value = _l1.get(key)
    if value is not None:
        with _stats_lock:
            _stats["l1_hit"] += 1
        return value

    with _stats_lock:
        _stats["l1_miss"] += 1

    if _redis_client is None:
        return None

    try:
        raw = _redis_client.get(key)
    except Exception:
        return None
    if not raw:
        with _stats_lock:
            _stats["redis_miss"] += 1
        return None

    try:
        decoded = json.loads(raw)
    except Exception:
        return None

    # Small L1 hot-cache to reduce Redis traffic.
    _l1.set(key, decoded, ttl_seconds=5)
    with _stats_lock:
        _stats["redis_hit"] += 1
    return decoded


def set_json(key: str, value: Any, ttl_seconds: int) -> None:
    encoded = jsonable_encoder(value)
    _l1.set(key, encoded, ttl_seconds=ttl_seconds)
    if _redis_client is None:
        return
    try:
        _redis_client.setex(
            key,
            max(1, int(ttl_seconds)),
            json.dumps(encoded, ensure_ascii=False, separators=(",", ":")),
        )
    except Exception:
        with _stats_lock:
            _stats["set_err"] += 1
    else:
        with _stats_lock:
            _stats["set_ok"] += 1


def _version_key(namespace: str) -> str:
    return f"cache:version:{namespace}"


def get_version(namespace: str) -> int:
    if _redis_client is None:
        return _versions_l1.get(namespace, 1)

    try:
        raw = _redis_client.get(_version_key(namespace))
        if raw:
            return int(raw)
        _redis_client.set(_version_key(namespace), "1")
        return 1
    except Exception:
        return _versions_l1.get(namespace, 1)


def bump_version(namespace: str) -> int:
    if _redis_client is None:
        _versions_l1[namespace] = _versions_l1.get(namespace, 1) + 1
        return _versions_l1[namespace]

    try:
        return int(_redis_client.incr(_version_key(namespace)))
    except Exception:
        _versions_l1[namespace] = _versions_l1.get(namespace, 1) + 1
        return _versions_l1[namespace]


def versioned_key(namespace: str, suffix: str) -> str:
    version = get_version(namespace)
    return f"cache:{namespace}:v{version}:{suffix}"


def cache_stats() -> dict[str, Any]:
    with _stats_lock:
        stats = dict(_stats)
    stats["redis_enabled"] = bool(_redis_client is not None)
    return stats


def redis_key_ttls(patterns: list[str], *, max_keys_per_pattern: int = 25) -> list[dict[str, Any]]:
    if _redis_client is None:
        return []

    keys: list[dict[str, Any]] = []
    try:
        for pattern in patterns:
            for idx, key in enumerate(_redis_client.scan_iter(match=pattern, count=200)):
                if idx >= max_keys_per_pattern:
                    break
                keys.append({"key": key, "ttl": int(_redis_client.ttl(key))})
    except Exception:
        return keys
    return keys
