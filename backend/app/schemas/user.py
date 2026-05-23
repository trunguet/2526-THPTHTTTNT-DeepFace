from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


UserRole = Literal["admin", "user"]


class AdminUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    role: UserRole
    created_at: datetime


class AdminUserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=255)
    role: UserRole = "user"


class AdminUserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=1, max_length=100)
    password: str | None = Field(default=None, min_length=1, max_length=255)
    role: UserRole | None = None
