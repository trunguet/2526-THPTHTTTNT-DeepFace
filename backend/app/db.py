from collections.abc import Generator
from datetime import datetime, timezone
import time

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker

from app.config import DATABASE_URL


engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), default="")
    department: Mapped[str] = mapped_column(String(255), default="")
    image_object_key: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    embedding_status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    logs: Mapped[list["AccessLog"]] = relationship(back_populates="employee")


class AccessLog(Base):
    __tablename__ = "access_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    employee_db_id: Mapped[int | None] = mapped_column(ForeignKey("employees.id"), nullable=True)
    employee_id: Mapped[str] = mapped_column(String(64), default="")
    employee_name: Mapped[str] = mapped_column(String(255), default="")
    camera_location: Mapped[str] = mapped_column(String(255), default="Main Gate")
    access_type: Mapped[str] = mapped_column(String(32), default="check_in")
    status: Mapped[str] = mapped_column(String(32), default="stranger")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    snapshot_object_key: Mapped[str] = mapped_column(Text, default="")
    image_url: Mapped[str] = mapped_column(Text, default="")
    alert_dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now_utc)

    employee: Mapped[Employee | None] = relationship(back_populates="logs")


def init_db(retries: int = 30) -> None:
    for attempt in range(retries):
        try:
            Base.metadata.create_all(bind=engine)
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
