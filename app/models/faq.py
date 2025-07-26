from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class FAQ(Base):
    __tablename__ = 'faqs'
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False)
    question = Column(String(500), nullable=False)
    answer = Column(String(2000), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    business = relationship("Business", back_populates="faqs")
