import os
from collections.abc import Callable
from typing import Any


TRUE_VALUES = {"1", "true", "yes", "on"}


def env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in TRUE_VALUES


def run_startup_step(label: str, action: Callable[[], Any], *, strict: bool) -> bool:
    try:
        action()
    except Exception as exc:
        print(f"{label} failed: {exc}", flush=True)
        if strict:
            raise
        return False
    return True
