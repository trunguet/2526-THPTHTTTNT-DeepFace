from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator


AccessDecision = Literal["processing", "granted", "denied", "error"]


class AccessCheckRequest(BaseModel):
    camera_id: int
    image_key: str | None = Field(default=None, min_length=1)
    image_path: str | None = Field(default=None, min_length=1)

    @model_validator(mode="after")
    def require_image_reference(self) -> "AccessCheckRequest":
        if self.image_key is None and self.image_path is None:
            raise ValueError("image_key or image_path is required")
        return self

    @property
    def resolved_image_key(self) -> str:
        value = self.image_key or self.image_path
        if value is None:
            raise ValueError("image_key or image_path is required")
        return value


class AccessCheckResponse(BaseModel):
    log_id: int
    job_id: str | None = None
    status: AccessDecision
    employee_id: int | None
    employee_name: str | None = None
    camera_id: int
    score: float | None
    image_key: str
    image_path: str
    message: str
    created_at: datetime


class AccessSnapshotUploadResponse(BaseModel):
    object_key: str
    bucket: str
    content_type: str
    size: int
