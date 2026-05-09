from collections.abc import Generator
from datetime import datetime, timezone
import re
import time

from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.dialects.mysql import TIMESTAMP
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import DATABASE_SSL, DATABASE_URL


def _connect_args() -> dict:
    # Ensure all MySQL sessions use Vietnam timezone (+07:00) for TIMESTAMP
    # conversion and functions like NOW()/CURRENT_TIMESTAMP.
    args: dict = {"init_command": "SET SESSION time_zone = '+07:00'"}
    if DATABASE_SSL:
        args["ssl"] = {"check_hostname": False}
    return args


def _ensure_database_exists() -> None:
    url = make_url(DATABASE_URL)
    database = url.database
    if not database:
        return
    if not re.fullmatch(r"[A-Za-z0-9_]+", database):
        raise RuntimeError(f"Unsafe database name: {database}")

    server_url = url.set(database="")
    server_engine = create_engine(
        server_url,
        pool_pre_ping=True,
        connect_args=_connect_args(),
    )
    try:
        with server_engine.begin() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{database}`"))
    finally:
        server_engine.dispose()


engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=_connect_args())
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_required_schema() -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS admin_accounts (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            username VARCHAR(50) NOT NULL,
            password_salt VARCHAR(64) NOT NULL,
            password_hash VARCHAR(128) NOT NULL,
            password_iterations INT NOT NULL DEFAULT 210000,
            full_name VARCHAR(100) NULL,
            email VARCHAR(255) NULL,
            role ENUM('admin','super_admin') NOT NULL DEFAULT 'admin',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            last_login_at TIMESTAMP NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY ux_admin_accounts_username (username)
        ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS employees (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            employee_code VARCHAR(50) NOT NULL,
            full_name VARCHAR(100) NOT NULL,
            email VARCHAR(100) NULL,
            department VARCHAR(100) NULL,
            minio_image_path VARCHAR(255),
            is_vectorized BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            UNIQUE KEY ux_employees_employee_code (employee_code)
        ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS employees_backup (
            backup_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            original_id BIGINT,
            full_name VARCHAR(100),
            minio_image_path VARCHAR(255),
            action_type ENUM('UPDATE','DELETE'),
            action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            employee_code VARCHAR(50) NULL,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('SUCCESS','FAILED','STRANGER') NOT NULL,
            minio_snapshot_path VARCHAR(255) NULL,
            handled TINYINT DEFAULT 0,
            FOREIGN KEY (employee_code) REFERENCES employees(employee_code) ON DELETE SET NULL
        ) ENGINE=InnoDB CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))

        # Backfill schema changes for existing databases created with older versions.
        # Note: CREATE TABLE IF NOT EXISTS will not add missing columns.
        def column_exists(table: str, column: str) -> bool:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(1) AS cnt
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = :table_name
                      AND column_name = :column_name
                    """
                ),
                {"table_name": table, "column_name": column},
            ).mappings().first()
            return bool(row and row.get("cnt"))

        def column_type(table: str, column: str) -> str:
            row = conn.execute(
                text(
                    """
                    SELECT column_type AS column_type
                    FROM information_schema.columns
                    WHERE table_schema = DATABASE()
                      AND table_name = :table_name
                      AND column_name = :column_name
                    LIMIT 1
                    """
                ),
                {"table_name": table, "column_name": column},
            ).mappings().first()
            return str(row.get("column_type") or "") if row else ""

        def index_exists(table: str, index: str) -> bool:
            row = conn.execute(
                text(
                    """
                    SELECT COUNT(1) AS cnt
                    FROM information_schema.statistics
                    WHERE table_schema = DATABASE()
                      AND table_name = :table_name
                      AND index_name = :index_name
                    """
                ),
                {"table_name": table, "index_name": index},
            ).mappings().first()
            return bool(row and row.get("cnt"))

        # Employees extended columns
        if not column_exists("employees", "employee_code"):
            conn.execute(text("ALTER TABLE employees ADD COLUMN employee_code VARCHAR(50) NULL"))
        if not column_exists("employees", "email"):
            conn.execute(text("ALTER TABLE employees ADD COLUMN email VARCHAR(100) NULL"))
        if not column_exists("employees", "department"):
            conn.execute(text("ALTER TABLE employees ADD COLUMN department VARCHAR(100) NULL"))

        # Backfill: ensure employee_code is present for older rows.
        conn.execute(
            text(
                """
                UPDATE employees
                SET employee_code = CAST(id AS CHAR)
                WHERE employee_code IS NULL OR employee_code = ''
                """
            )
        )

        # Enforce NOT NULL + expected length. Do this after backfill.
        conn.execute(text("ALTER TABLE employees MODIFY COLUMN employee_code VARCHAR(50) NOT NULL"))

        # Unique business identifier
        if not index_exists("employees", "ux_employees_employee_code"):
            conn.execute(text("CREATE UNIQUE INDEX ux_employees_employee_code ON employees (employee_code)"))

        # Admin accounts backfill (best-effort; keep schema additive).
        if not index_exists("admin_accounts", "ux_admin_accounts_username"):
            conn.execute(text("CREATE UNIQUE INDEX ux_admin_accounts_username ON admin_accounts (username)"))

        if not column_exists("admin_accounts", "password_salt"):
            conn.execute(text("ALTER TABLE admin_accounts ADD COLUMN password_salt VARCHAR(64) NULL"))
        if not column_exists("admin_accounts", "password_iterations"):
            conn.execute(
                text("ALTER TABLE admin_accounts ADD COLUMN password_iterations INT NOT NULL DEFAULT 210000")
            )
        if column_exists("admin_accounts", "role"):
            role_type = column_type("admin_accounts", "role").lower()
            if "enum" in role_type and "super_admin" not in role_type:
                conn.execute(text("ALTER TABLE admin_accounts MODIFY COLUMN role ENUM('admin','super_admin')"))

        # Attendance logs extended columns
        if not column_exists("attendance_logs", "employee_code"):
            # Migrate from older schema that used numeric employee_id.
            conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN employee_code VARCHAR(50) NULL"))

        # Backfill: if older logs used numeric employee_id, map it to employee_code.
        # Run this even when the employee_code column already exists (idempotent).
        if column_exists("attendance_logs", "employee_id") and column_exists("attendance_logs", "employee_code"):
            conn.execute(
                text(
                    """
                    UPDATE attendance_logs al
                    JOIN employees e ON e.id = al.employee_id
                    SET al.employee_code = e.employee_code
                    WHERE al.employee_id IS NOT NULL AND (al.employee_code IS NULL OR al.employee_code = '')
                    """
                )
            )

        if not column_exists("attendance_logs", "handled"):
            conn.execute(text("ALTER TABLE attendance_logs ADD COLUMN handled TINYINT DEFAULT 0"))

        # Performance: look up "today" scans by employee efficiently.
        if not index_exists("attendance_logs", "idx_attendance_employee_scan_time"):
            conn.execute(
                text(
                    "CREATE INDEX idx_attendance_employee_scan_time "
                    "ON attendance_logs (employee_code, scan_time)"
                )
            )

        # Best-effort: add FK on employee_code for older schemas (ignore if it already exists).
        # MySQL requires an explicit constraint name to drop/replace; keep this additive.
        try:
            conn.execute(
                text(
                    "ALTER TABLE attendance_logs "
                    "ADD CONSTRAINT fk_attendance_employee_code "
                    "FOREIGN KEY (employee_code) REFERENCES employees(employee_code) "
                    "ON DELETE SET NULL"
                )
            )
        except Exception:
            pass


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_code: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(100), nullable=True)
    department: Mapped[str | None] = mapped_column(String(100), nullable=True)
    minio_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_vectorized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )

    logs: Mapped[list["AttendanceLog"]] = relationship(back_populates="employee")


class EmployeeBackup(Base):
    __tablename__ = "employees_backup"

    backup_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    minio_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_type: Mapped[str] = mapped_column(Enum("UPDATE", "DELETE"))
    action_time: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_code: Mapped[str | None] = mapped_column(
        ForeignKey("employees.employee_code", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scan_time: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    status: Mapped[str] = mapped_column(Enum("SUCCESS", "FAILED", "STRANGER"))
    minio_snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    handled: Mapped[bool] = mapped_column(Boolean, default=False)

    employee: Mapped[Employee | None] = relationship(back_populates="logs")


AccessLog = AttendanceLog


class AdminAccount(Base):
    __tablename__ = "admin_accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    username: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    password_salt: Mapped[str | None] = mapped_column(String(64), nullable=True)
    password_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    password_iterations: Mapped[int] = mapped_column(Integer, nullable=False, default=210000)
    role: Mapped[str] = mapped_column(Enum("admin", "super_admin"), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_login_at: Mapped[datetime | None] = mapped_column(TIMESTAMP, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP,
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP"),
        server_onupdate=text("CURRENT_TIMESTAMP"),
    )


def init_db(retries: int = 30) -> None:
    for attempt in range(retries):
        try:
            _ensure_database_exists()
            _ensure_required_schema()
            return
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(1)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
