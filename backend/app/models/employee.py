from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.access_log import AccessLog
    from app.models.face_embedding import FaceEmbedding


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(150), index=True)
    department: Mapped[str | None] = mapped_column(String(150), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)
    embedding_status: Mapped[str] = mapped_column(
        String(50),
        default="none",
        server_default="none",
        index=True,
    )
    embedding_error: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    embeddings: Mapped[list["FaceEmbedding"]] = relationship(
        back_populates="employee",
        cascade="all, delete-orphan",
    )
    access_logs: Mapped[list["AccessLog"]] = relationship(back_populates="employee")
