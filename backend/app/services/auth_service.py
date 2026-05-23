from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_access_token, verify_password
from app.models.user import User
from app.repositories.user_repository import get_user_by_id, get_user_by_username
from app.schemas.auth import TokenResponse


def authenticate_user(db: Session, username: str, password: str) -> User | None:
    user = get_user_by_username(db, username=username)
    if user is None:
        return None

    if not verify_password(password, user.password_hash):
        return None

    return user


def build_token_response(user: User) -> TokenResponse:
    access_token = create_access_token(
        subject=str(user.id),
        claims={"username": user.username, "role": user.role},
    )
    return TokenResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=user,
    )


def get_user_from_token(db: Session, token: str) -> User | None:
    payload = decode_access_token(token)
    if payload is None:
        return None

    subject = payload.get("sub")
    if subject is None:
        return None

    try:
        user_id = int(subject)
    except (TypeError, ValueError):
        return None

    return get_user_by_id(db, user_id=user_id)
