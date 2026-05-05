from collections.abc import Generator
from datetime import datetime, timezone
import re
import time

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Integer, String, create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import DATABASE_SSL, DATABASE_URL


def _connect_args() -> dict:
    if DATABASE_SSL:
        return {"ssl": {"check_hostname": False}}
    return {}


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
        CREATE TABLE IF NOT EXISTS employees (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(100) NOT NULL,
            minio_image_path VARCHAR(255),
            is_vectorized BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS employees_backup (
            backup_id BIGINT AUTO_INCREMENT PRIMARY KEY,
            original_id BIGINT,
            full_name VARCHAR(100),
            minio_image_path VARCHAR(255),
            action_type ENUM('UPDATE','DELETE'),
            action_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
        """
        CREATE TABLE IF NOT EXISTS attendance_logs (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            employee_id BIGINT NULL,
            scan_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status ENUM('SUCCESS','FAILED','STRANGER') NOT NULL,
            minio_snapshot_path VARCHAR(255) NULL,
            FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE SET NULL
        ) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
        """,
    ]

    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100))
    minio_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_vectorized: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc, onupdate=now_utc)

    logs: Mapped[list["AttendanceLog"]] = relationship(back_populates="employee")


class EmployeeBackup(Base):
    __tablename__ = "employees_backup"

    backup_id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    original_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    full_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    minio_image_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    action_type: Mapped[str] = mapped_column(Enum("UPDATE", "DELETE"))
    action_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)


class AttendanceLog(Base):
    __tablename__ = "attendance_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
    scan_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    status: Mapped[str] = mapped_column(Enum("SUCCESS", "FAILED", "STRANGER"))
    minio_snapshot_path: Mapped[str | None] = mapped_column(String(255), nullable=True)

    employee: Mapped[Employee | None] = relationship(back_populates="logs")


AccessLog = AttendanceLog


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
