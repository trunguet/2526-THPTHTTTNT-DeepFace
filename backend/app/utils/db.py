import os
from typing import Any, Dict, Iterable, Optional, Tuple

import pymysql


def _get_db_name() -> str:
    return os.getenv("TIDB_DB", "DB_Employee")


def get_connection() -> pymysql.connections.Connection:
    host = os.getenv("TIDB_HOST")
    user = os.getenv("TIDB_USER")
    password = os.getenv("TIDB_PASSWORD")

    if not host or not user or not password:
        raise RuntimeError("Missing TIDB_HOST/TIDB_USER/TIDB_PASSWORD in environment")

    port = int(os.getenv("TIDB_PORT", "4000"))
    db = _get_db_name()
    ssl_required = os.getenv("TIDB_SSL", "REQUIRE").upper() == "REQUIRE"

    config: Dict[str, Any] = {
        "host": host,
        "user": user,
        "password": password,
        "port": port,
        "database": db,
        "autocommit": True,
        "cursorclass": pymysql.cursors.DictCursor,
        "init_command": "SET SESSION time_zone = '+07:00'",
    }

    if ssl_required:
        config["ssl"] = {}

    conn = pymysql.connect(**config)
    ensure_schema(conn)
    return conn


def _column_exists(conn: pymysql.connections.Connection, table: str, column: str) -> bool:
    sql = (
        "SELECT COUNT(1) AS cnt FROM information_schema.columns "
        "WHERE table_schema = %s AND table_name = %s AND column_name = %s"
    )
    db = _get_db_name()
    with conn.cursor() as cursor:
        cursor.execute(sql, (db, table, column))
        row = cursor.fetchone()
        return bool(row and row.get("cnt"))


def _add_column(conn: pymysql.connections.Connection, table: str, column_ddl: str) -> None:
    with conn.cursor() as cursor:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column_ddl}")


def _index_exists(conn: pymysql.connections.Connection, table: str, index: str) -> bool:
    sql = (
        "SELECT COUNT(1) AS cnt FROM information_schema.statistics "
        "WHERE table_schema = %s AND table_name = %s AND index_name = %s"
    )
    db = _get_db_name()
    with conn.cursor() as cursor:
        cursor.execute(sql, (db, table, index))
        row = cursor.fetchone()
        return bool(row and row.get("cnt"))


def ensure_schema(conn: pymysql.connections.Connection) -> None:
    with conn.cursor() as cursor:
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS employees ("
            "id BIGINT AUTO_INCREMENT PRIMARY KEY,"
            "employee_code VARCHAR(50) NOT NULL,"
            "full_name VARCHAR(100) NOT NULL,"
            "email VARCHAR(100) NULL,"
            "department VARCHAR(100) NULL,"
            "minio_image_path VARCHAR(255),"
            "is_vectorized BOOLEAN DEFAULT FALSE,"
            "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,"
            "UNIQUE KEY ux_employees_employee_code (employee_code)"
            ") ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

        cursor.execute(
            "CREATE TABLE IF NOT EXISTS attendance_logs ("
            "id BIGINT AUTO_INCREMENT PRIMARY KEY,"
            "employee_id BIGINT NULL,"
            "scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,"
            "status ENUM('SUCCESS','FAILED','STRANGER') NOT NULL,"
            "minio_snapshot_path VARCHAR(255) NULL"
            ") CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )

    extra_columns = [
        ("employees", "employee_code VARCHAR(50) NULL"),
        ("employees", "email VARCHAR(100) NULL"),
        ("employees", "department VARCHAR(100) NULL"),
        ("attendance_logs", "camera_id VARCHAR(64) NULL"),
        ("attendance_logs", "client_id VARCHAR(64) NULL"),
        ("attendance_logs", "similarity FLOAT NULL"),
        ("attendance_logs", "handled TINYINT DEFAULT 0"),
    ]

    for table, ddl in extra_columns:
        column_name = ddl.split(" ", 1)[0]
        if not _column_exists(conn, table, column_name):
            _add_column(conn, table, ddl)

    # Backfill and enforce constraints for employee_code (older schemas created it as NULL).
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE employees SET employee_code = CAST(id AS CHAR) "
            "WHERE employee_code IS NULL OR employee_code = ''"
        )
        cursor.execute("ALTER TABLE employees MODIFY COLUMN employee_code VARCHAR(50) NOT NULL")
        if not _index_exists(conn, "employees", "ux_employees_employee_code"):
            cursor.execute("CREATE UNIQUE INDEX ux_employees_employee_code ON employees (employee_code)")
