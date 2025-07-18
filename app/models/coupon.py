from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid
from app.db.base import Base
from app.models.enums import CouponType

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False)

    type = Column(Enum(CouponType), nullable=False)  # platform or business

    # Platform-specific
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # sales/influencer
    platform_target = Column(String, nullable=True)  # optional: "influencer", "sales", "marketing", etc.

    # Business-specific
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)

    # Common
    discount_type = Column(String, default="flat")  # flat or percentage
    discount_value = Column(Float, nullable=False)

    usage_limit = Column(Integer, nullable=True)  # max total usage
    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="coupons")
    business = relationship("Business", back_populates="coupons")
