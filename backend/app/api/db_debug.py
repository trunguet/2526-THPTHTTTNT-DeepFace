from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.config import DATABASE_URL
from app.db import get_db
from app.security import require_admin


router = APIRouter(prefix="/api/debug", tags=["debug"], dependencies=[Depends(require_admin)])


def _database_target() -> dict[str, Any]:
    url = make_url(DATABASE_URL)
    return {
        "driver": url.drivername,
        "username": url.username,
        "host": url.host,
        "port": url.port,
        "database": url.database,
    }


@router.get("/db")
def database_debug(db: Session = Depends(get_db)) -> dict[str, Any]:
    server = db.execute(
        text(
            """
            SELECT
                DATABASE() AS database_name,
                @@hostname AS server_hostname,
                @@port AS server_port,
                @@version AS server_version,
                @@time_zone AS session_time_zone
            """
        )
    ).mappings().one()

    counts = db.execute(
        text(
            """
            SELECT
                (SELECT COUNT(*) FROM employees) AS employees,
                (SELECT COUNT(*) FROM attendance_logs) AS attendance_logs,
                (SELECT COUNT(*) FROM admin_accounts) AS admin_accounts
            """
        )
    ).mappings().one()

    recent_employees = db.execute(
        text(
            """
            SELECT id, employee_code, full_name, email, department, created_at
            FROM employees
            ORDER BY id DESC
            LIMIT 10
            """
        )
    ).mappings().all()

    return {
        "configured_target": _database_target(),
        "connected_server": dict(server),
        "counts": dict(counts),
        "recent_employees": [dict(row) for row in recent_employees],
    }
