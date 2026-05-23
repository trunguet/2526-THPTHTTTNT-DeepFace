from fastapi import APIRouter

from app.core.deps import CurrentUser, DbSession
from app.schemas.log import AccessLogRead
from app.services.log_service import get_access_logs


router = APIRouter(prefix="/logs", tags=["logs"])


@router.get("", response_model=list[AccessLogRead])
def list_access_log_records(
    db: DbSession,
    current_user: CurrentUser,
) -> list[AccessLogRead]:
    return get_access_logs(db)
