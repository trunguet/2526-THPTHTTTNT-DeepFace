from sqlalchemy.orm import Session

from app.models.access_log import AccessLog
from app.repositories.access_log_repository import list_access_logs


def get_access_logs(db: Session) -> list[AccessLog]:
    return list_access_logs(db)
