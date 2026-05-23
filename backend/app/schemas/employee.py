from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


EmployeeStatus = Literal["active", "inactive"]
EmbeddingStatus = Literal["none", "pending", "success", "error"]


class EmployeeBase(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    status: EmployeeStatus = "active"


class EmployeeCreate(EmployeeBase):
    pass


class EmployeeUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    department: str | None = Field(default=None, max_length=150)
    status: EmployeeStatus | None = None


class EmployeeRead(EmployeeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    embedding_status: EmbeddingStatus = "none"
    embedding_error: str | None = None
    created_at: datetime


class EmployeeEmbeddingJobRequest(BaseModel):
    image_key: str | None = Field(default=None, min_length=1, max_length=1000)
    image_path: str | None = Field(default=None, min_length=1, max_length=1000)

    @model_validator(mode="after")
    def require_image_reference(self) -> "EmployeeEmbeddingJobRequest":
        if self.image_key is None and self.image_path is None:
            raise ValueError("image_key or image_path is required")
        return self

    @property
    def resolved_image_key(self) -> str:
        value = self.image_key or self.image_path
        if value is None:
            raise ValueError("image_key or image_path is required")
        return value


class EmployeeEmbeddingJobResponse(BaseModel):
    job_id: str
    type: str
    employee_id: int
    image_key: str
    image_path: str
    queue_name: str
    message: str


class ImageUploadResponse(BaseModel):
    object_key: str
    bucket: str
    content_type: str
    size: int
    job_id: str | None = None
    type: str | None = None
    employee_id: int | None = None
    queue_name: str | None = None
    message: str | None = None
