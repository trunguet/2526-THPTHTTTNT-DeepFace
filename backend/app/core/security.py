import base64
import binascii
import json
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings


PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 260_000
TOKEN_ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_HASH_ITERATIONS,
    )

    salt_text = base64.b64encode(salt).decode("ascii")
    hash_text = base64.b64encode(password_hash).decode("ascii")
    return (
        f"{PASSWORD_HASH_ALGORITHM}"
        f"${PASSWORD_HASH_ITERATIONS}"
        f"${salt_text}"
        f"${hash_text}"
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations_text, salt_text, expected_hash = password_hash.split("$")
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        iterations = int(iterations_text)
        salt = base64.b64decode(salt_text.encode("ascii"))
        candidate_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        candidate_text = base64.b64encode(candidate_hash).decode("ascii")
    except (binascii.Error, ValueError, TypeError):
        return False

    return secrets.compare_digest(candidate_text, expected_hash)


def create_access_token(subject: str, claims: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    if claims:
        payload.update(claims)

    header = {"alg": TOKEN_ALGORITHM, "typ": "JWT"}
    signing_input = (
        f"{_base64url_json(header)}.{_base64url_json(payload)}"
    )
    signature = _sign(signing_input)
    return f"{signing_input}.{signature}"


def decode_access_token(token: str) -> dict[str, Any] | None:
    try:
        header_text, payload_text, signature = token.split(".")
        signing_input = f"{header_text}.{payload_text}"
        expected_signature = _sign(signing_input)
        if not secrets.compare_digest(signature, expected_signature):
            return None

        header = _base64url_decode_json(header_text)
        if header.get("alg") != TOKEN_ALGORITHM:
            return None

        payload = _base64url_decode_json(payload_text)
        expires_at = int(payload["exp"])
    except (binascii.Error, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return None

    if expires_at < int(datetime.now(timezone.utc).timestamp()):
        return None

    return payload


def _base64url_json(data: dict[str, Any]) -> str:
    json_bytes = json.dumps(data, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    return base64.urlsafe_b64encode(json_bytes).rstrip(b"=").decode("ascii")


def _base64url_decode_json(data: str) -> dict[str, Any]:
    padding = "=" * (-len(data) % 4)
    raw = base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def _sign(signing_input: str) -> str:
    signature = hmac.new(
        settings.auth_secret_key.encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")
