from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

from app.models.enums import ConditionOperator, OfferConditionType, OfferRewardType, OfferType

class Offer(Base):
    __tablename__ = "offers"

    id = Column(Integer, primary_key=True)
    
    # General
    name = Column(JSONB, nullable=False)
    description = Column(JSONB, nullable=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)  # null = platform offer
    offer_type = Column(Enum(OfferType), nullable=False)  # enum: flat, percentage, bxgy, bundle, etc.

    # Behavior
    auto_apply = Column(Boolean, default=True)
    can_stack_with_coupon = Column(Boolean, default=False)

    # Timing & Validity
    valid_from = Column(DateTime(timezone=True))
    valid_to = Column(DateTime(timezone=True))
    usage_limit = Column(Integer, nullable=True)       # per user
    available_limit = Column(Integer, nullable=True)   # total usage

    is_active = Column(Boolean, default=True)

    created_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    business = relationship("Business", back_populates="offers")
    conditions = relationship("OfferCondition", back_populates="offer", cascade="all, delete")
    rewards = relationship("OfferReward", back_populates="offer", cascade="all, delete")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_offer")

class OfferCondition(Base):
    __tablename__ = "offer_conditions"

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    

    condition_type = Column(Enum(OfferConditionType), nullable=False)  # e.g., PRODUCT, SERVICE, CATEGORY, CART_TOTAL, FIRST_ORDER
    operator = Column(Enum(ConditionOperator), nullable=False, default="equals")  # "equals", "in", "gte", "lte"
    value = Column(JSONB, nullable=False)  # depends on type (e.g., product_id list, float value, boolean)
    quantity = Column(Integer, nullable=True)  # For product quantity-based conditions

    offer = relationship("Offer", back_populates="conditions")

class OfferReward(Base):
    __tablename__ = "offer_rewards"

    id = Column(Integer, primary_key=True)
    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=False)
    offer = relationship("Offer", back_populates="rewards")

    reward_type = Column(Enum(OfferRewardType), nullable=False)  # FLAT, PERCENTAGE, FREE_PRODUCT, DISCOUNTED_PRODUCT
    value = Column(Float, nullable=True)  # e.g., 50 for ₹50 flat or 10% discount

    item_type = Column(String, nullable=True)  # "product" or "service", only for item-based rewards
    item_id = Column(Integer, nullable=True)   # ID of product/service to be given as reward
    quantity = Column(Integer, nullable=True)  # e.g., 1 free item
    max_discount = Column(Float, nullable=True)  # For percentage rewards
