from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.config import ADMIN_AUTH_SECRET, ADMIN_TOKEN_TTL_SECONDS
from app.db import AdminAccount, get_db


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padded = value + "=" * ((4 - (len(value) % 4)) % 4)
    return base64.urlsafe_b64decode(padded.encode("ascii"))


def _now() -> int:
    return int(time.time())


def hash_password(password: str, *, iterations: int = 210_000) -> tuple[str, str, int]:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    return _b64url_encode(salt), _b64url_encode(dk), iterations


def verify_password(password: str, salt_b64: str, hash_b64: str, iterations: int) -> bool:
    if not salt_b64:
        return False
    salt = _b64url_decode(salt_b64)
    expected = _b64url_decode(hash_b64)
    got = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations), dklen=len(expected))
    return hmac.compare_digest(got, expected)


def create_admin_token(*, username: str, role: str, ttl_seconds: int | None = None) -> str:
    ttl = int(ttl_seconds or ADMIN_TOKEN_TTL_SECONDS)
    header = {"alg": "HS256", "typ": "JWT"}
    iat = _now()
    payload = {"sub": username, "role": role, "type": "admin", "iat": iat, "exp": iat + ttl}
    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
            _b64url_encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
        ]
    )
    sig = hmac.new(ADMIN_AUTH_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(sig)}"


@dataclass(frozen=True)
class AdminIdentity:
    username: str
    role: str


def decode_and_verify_admin_token(token: str) -> AdminIdentity:
    parts = (token or "").split(".")
    if len(parts) != 3:
        raise ValueError("Invalid token format")

    header_b64, payload_b64, sig_b64 = parts
    signing_input = f"{header_b64}.{payload_b64}"
    expected = hmac.new(ADMIN_AUTH_SECRET.encode("utf-8"), signing_input.encode("ascii"), hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url_encode(expected), sig_b64):
        raise ValueError("Invalid token signature")

    payload = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
    if payload.get("type") != "admin":
        raise ValueError("Invalid token type")

    exp = int(payload.get("exp") or 0)
    if exp <= _now():
        raise ValueError("Token expired")

    username = str(payload.get("sub") or "").strip()
    role = str(payload.get("role") or "admin").strip() or "admin"
    if not username:
        raise ValueError("Invalid token subject")

    return AdminIdentity(username=username, role=role)


def _extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    if not auth.lower().startswith("bearer "):
        return None
    return auth.split(" ", 1)[1].strip() or None


def require_admin(
    request: Request,
    db: Session = Depends(get_db),
) -> AdminAccount:
    token = _extract_bearer_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Missing Authorization token")

    try:
        identity = decode_and_verify_admin_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    admin = db.query(AdminAccount).filter(AdminAccount.username == identity.username).first()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="Admin account is disabled")

    return admin
