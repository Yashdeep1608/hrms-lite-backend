from sqlalchemy import UUID, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import CartOrderSource

class Cart(Base):
    __tablename__ = "carts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False,index=True)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False,index=True)
    anonymous_id = Column(String, nullable=True)
    source = Column(Enum(CartOrderSource), nullable=False,index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    business = relationship("Business", back_populates="carts")
    business_contact = relationship("BusinessContact", back_populates="carts")
    items = relationship("CartItem", back_populates="cart", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_carts")

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

    quantity = Column(Integer, default=1)

    # Service-specific optional fields
    time_slot = Column(String, nullable=True)
    start_date = Column(Date, nullable=True)
    day = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    cart = relationship("Cart", back_populates="items")