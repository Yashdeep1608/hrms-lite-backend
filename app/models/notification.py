from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean,String,Enum, Text
from datetime import datetime, timezone
from app.db.base import Base
import enum

class NotificationType(str, enum.Enum):
    SUPPORT = "support"
    PRODUCT = "product"
    ORDER = "order"
    GENERAL = "general"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    type = Column(Enum(NotificationType), nullable=False)
    message = Column(Text, nullable=False)
    url = Column(String, nullable=True)  # frontend redirection link
    is_read = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone = True),default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
