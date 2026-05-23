from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


AccessLogStatus = Literal["processing", "granted", "denied", "error"]


class AccessLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    employee_id: int | None
    employee_name: str | None
    camera_id: int | None
    status: AccessLogStatus
    score: float | None
    image_path: str | None
    message: str | None
    created_at: datetime
