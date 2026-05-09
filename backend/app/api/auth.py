from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import AdminAccount, get_db
from app.schemas import AdminLoginRequest, AdminRegisterRequest
from app.security import create_admin_token, hash_password, require_admin, verify_password


router = APIRouter(prefix="/api/auth", tags=["auth"])


def _normalize_username(username: str) -> str:
    value = str(username or "").strip().lower()
    if not value or len(value) < 3:
        raise ValueError("Username must be at least 3 characters")
    if len(value) > 50:
        raise ValueError("Username is too long (max 50 characters)")
    return value


@router.get("/admin/exists")
def admin_exists(db: Session = Depends(get_db)) -> dict[str, bool]:
    exists = db.query(AdminAccount.id).limit(1).count() > 0
    return {"exists": bool(exists)}


@router.post("/admin/register")
def register_admin(payload: AdminRegisterRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        username = _normalize_username(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    password = str(payload.password or "")
    if len(password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    exists = db.query(AdminAccount).filter(AdminAccount.username == username).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="Admin account already exists")

    # First registered account becomes super_admin (bootstrap).
    role = "super_admin" if db.query(AdminAccount.id).limit(1).count() == 0 else "admin"

    salt, password_hash, iterations = hash_password(password)
    admin = AdminAccount(
        username=username,
        password_salt=salt,
        password_hash=password_hash,
        password_iterations=iterations,
        role=role,
        is_active=True,
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)

    token = create_admin_token(username=admin.username, role=admin.role)
    return {"token": token, "username": admin.username, "role": admin.role}


@router.post("/admin/login")
def login_admin(payload: AdminLoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    try:
        username = _normalize_username(payload.username)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    admin = db.query(AdminAccount).filter(AdminAccount.username == username).first()
    if admin is None or not admin.is_active:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not verify_password(payload.password, admin.password_salt, admin.password_hash, admin.password_iterations):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    from sqlalchemy import text

    db.query(AdminAccount).filter(AdminAccount.id == admin.id).update({"last_login_at": text("CURRENT_TIMESTAMP")})
    db.commit()

    token = create_admin_token(username=admin.username, role=admin.role)
    return {"token": token, "username": admin.username, "role": admin.role}


@router.get("/admin/me")
def admin_me(admin: AdminAccount = Depends(require_admin)) -> dict[str, Any]:
    return {"username": admin.username, "role": admin.role, "is_active": bool(admin.is_active)}
