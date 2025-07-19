from pydantic import BaseModel
from datetime import datetime
from enum import Enum


class NotificationCreate(BaseModel):
    user_id: int
    type: str
    message: str
    url: str | None = None

class NotificationOut(BaseModel):
    id: int
    type: str
    message: str
    url: str | None
    is_read: bool

