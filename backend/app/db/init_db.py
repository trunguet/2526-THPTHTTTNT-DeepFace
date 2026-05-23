from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.db.session import engine

# Import models so SQLAlchemy registers every table before create_all runs.
import app.models  # noqa: F401


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)
    ensure_employee_embedding_status_columns()
    ensure_face_embedding_source_image_column()
    ensure_access_log_message_column()


def ensure_employee_embedding_status_columns() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("employees"):
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("employees")
    }
    existing_indexes = {
        index["name"] for index in inspector.get_indexes("employees")
    }
    statements = []
    if "embedding_status" not in existing_columns:
        statements.append(
            "ALTER TABLE employees "
            "ADD COLUMN embedding_status VARCHAR(50) NOT NULL DEFAULT 'none'"
        )
    if "embedding_error" not in existing_columns:
        statements.append("ALTER TABLE employees ADD COLUMN embedding_error VARCHAR(1000)")
    if "ix_employees_embedding_status" not in existing_indexes:
        statements.append(
            "CREATE INDEX IF NOT EXISTS ix_employees_embedding_status "
            "ON employees (embedding_status)"
        )

    if not statements:
        return

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))


def ensure_face_embedding_source_image_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("face_embeddings"):
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("face_embeddings")
    }
    if "source_image_key" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(
            text("ALTER TABLE face_embeddings ADD COLUMN source_image_key TEXT")
        )


def ensure_access_log_message_column() -> None:
    inspector = inspect(engine)
    if not inspector.has_table("access_logs"):
        return

    existing_columns = {
        column["name"] for column in inspector.get_columns("access_logs")
    }
    if "message" in existing_columns:
        return

    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE access_logs ADD COLUMN message TEXT"))


def main() -> None:
    try:
        create_tables()
    except SQLAlchemyError as exc:
        raise SystemExit(f"Database initialization failed: {exc}") from exc

    print("Database tables are ready.")


if __name__ == "__main__":
    main()
