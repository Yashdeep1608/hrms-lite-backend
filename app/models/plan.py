from sqlalchemy import Column, DateTime, Integer, String, Float, Boolean, Interval
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.db.base import Base

class Plan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, unique=True)
    description = Column(String, nullable=True)
    
    price = Column(Float, nullable=False)  # Base price before discounts/tax
    offer_discount = Column(Float,nullable=False,default=0.0)
    duration_days = Column(Integer, nullable=False)  # Plan length in days (e.g., 30, 365)

    is_trial = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user_plans = relationship("UserPlan", back_populates="plan")
