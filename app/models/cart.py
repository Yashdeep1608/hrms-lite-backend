from sqlalchemy import UUID, Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import CartOrderSource, CartStatus

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False,index=True)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=True,index=True)
    anonymous_id = Column(String, nullable=True)
    source = Column(Enum(CartOrderSource), nullable=False,index=True)
    cart_status = Column(Enum(CartStatus), nullable=False, default=CartStatus.ACTIVE, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)
    coupon_discount = Column(Numeric(10, 2), default=0)
    coupon_removed = Column(Boolean,default=False)

    offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    offer_discount = Column(Numeric(10, 2), default=0)  # optional, total offer-based discount
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    business = relationship("Business", back_populates="carts")
    business_contact = relationship("BusinessContact", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    order = relationship("Order", back_populates="cart", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_carts")
    coupon = relationship("Coupon", foreign_keys=[coupon_id])
    coupon = relationship("Offer", foreign_keys=[offer_id])

class CartItem(Base):
    __tablename__ = "cart_items"

    id = Column(Integer, primary_key=True, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    item_type = Column(String, nullable=False)  # 'product', 'service', 'combo'
    item_id = Column(Integer, nullable=False)

    name = Column(String, nullable=False)
    actual_price = Column(Numeric(10, 2), nullable=False)
    final_price = Column(Numeric(10, 2), nullable=False)
    discount_price = Column(Numeric(10, 2), nullable=False)
    tax_amount = Column(Numeric(10, 2), nullable=True)
    tax_percentage = Column(Numeric(5, 2), nullable=True)

    quantity = Column(Integer, default=1)

    # Service-specific optional fields
    date = Column(Date, nullable=True)

    applied_offer_id = Column(Integer, ForeignKey("offers.id"), nullable=True)
    applied_coupon_id = Column(Integer, ForeignKey("coupons.id"), nullable=True)  # If you apply coupon to individual items

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    cart = relationship("Cart", back_populates="items")
    applied_offer = relationship("Offer", foreign_keys=[applied_offer_id])
    applied_coupon = relationship("Coupon", foreign_keys=[applied_coupon_id])