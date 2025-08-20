from sqlalchemy import Column, DateTime, Integer, String, Text
from datetime import datetime, timezone
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

class WebhookMessage(Base):
    __tablename__ = "webhook_messages"

    id = Column(Integer, primary_key=True, index=True)
    event_type = Column(String, index=True)
    payload = Column(JSONB) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
