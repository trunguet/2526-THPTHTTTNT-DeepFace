from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


CameraStatus = Literal["active", "inactive"]


class CameraBase(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    location: str | None = Field(default=None, max_length=255)
    stream_url: str | None = None
    status: CameraStatus = "active"


class CameraCreate(CameraBase):
    pass


class CameraUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=150)
    location: str | None = Field(default=None, max_length=255)
    stream_url: str | None = None
    status: CameraStatus | None = None


class CameraRead(CameraBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
