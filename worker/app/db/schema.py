from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    func,
)


metadata = MetaData()

employees = Table(
    "employees",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("code", String(50), nullable=False, unique=True),
    Column("name", String(150), nullable=False),
    Column("department", String(150), nullable=True),
    Column("status", String(50), nullable=False, default="active"),
    Column("embedding_status", String(50), nullable=False, default="none"),
    Column("embedding_error", String(1000), nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

face_embeddings = Table(
    "face_embeddings",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), nullable=False),
    Column("vector", JSON, nullable=False),
    Column("model_name", String(100), nullable=False),
    Column("source_image_key", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)

access_logs = Table(
    "access_logs",
    metadata,
    Column("id", Integer, primary_key=True),
    Column("employee_id", Integer, ForeignKey("employees.id"), nullable=True),
    Column("camera_id", Integer, nullable=True),
    Column("status", String(50), nullable=False),
    Column("score", Float, nullable=True),
    Column("image_path", Text, nullable=True),
    Column("message", Text, nullable=True),
    Column("created_at", DateTime(timezone=True), server_default=func.now()),
)
