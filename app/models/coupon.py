from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime, timezone
import uuid
from app.db.base import Base
from app.models.enums import CouponType

class Coupon(Base):
    __tablename__ = "coupons"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String, unique=True, nullable=False)
    type = Column(Enum(CouponType), nullable=False)  # platform or business

    # UI Friendly
    label = Column(String, nullable=False)
    description = Column(String, nullable=False)

    # Platform-specific
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # sales/influencer
    platform_target = Column(String, nullable=True)  # optional: "influencer", "sales", "marketing", etc.

    # Business-specific
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)

    # Discount Info
    discount_type = Column(String, default="flat")  # flat | percentage
    discount_value = Column(Float, nullable=False)
    max_discount_amount = Column(Float, nullable=True)

    min_cart_value = Column(Float, nullable=False, default=0)
    available_limit = Column(Integer, nullable=True) #available limit of coupon
    usage_limit = Column(Integer, nullable=True) # usage limit of coupon for contact/users/customers
    applied_count = Column(Integer, nullable=False, default=0)

    valid_from = Column(DateTime(timezone=True), nullable=True)
    valid_to = Column(DateTime(timezone=True), nullable=True)

    is_auto_applied = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)

    created_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)

    # ✅ JSONB Exclusions
    exclude_product_ids = Column(JSONB, default=[])
    exclude_service_ids = Column(JSONB, default=[])

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", foreign_keys=[user_id], back_populates="coupons")
    business = relationship("Business", back_populates="coupons")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_coupons")
