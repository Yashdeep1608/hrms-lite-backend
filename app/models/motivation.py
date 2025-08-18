from sqlalchemy import Column, Date, DateTime, Integer, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class DailyMotivation(Base):
    __tablename__ = "daily_motivations"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)  # date for which quote is applicable
    quote_en = Column(String(1000), nullable=False)
    quote_hi = Column(String(1000), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))    