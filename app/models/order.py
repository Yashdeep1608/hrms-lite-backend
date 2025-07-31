from sqlalchemy import UUID, Column, Date, DateTime, Enum, ForeignKey, Index, Integer, Boolean, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import CartOrderSource, CartOrderStatus, OrderPaymentMode,OrderPaymentStatus,OrderPaymentMethod

# orders table
class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True)
    order_number = Column(String, unique=True, nullable=False, index=True)
    cart_id = Column(Integer, ForeignKey("carts.id", ondelete="CASCADE"), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=True, index=True)
    anonymous_id = Column(UUID(as_uuid=True), nullable=True)
    source = Column(Enum(CartOrderSource), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    subtotal = Column(Numeric(10, 2), nullable=False)
    coupon_discount = Column(Numeric(10, 2), nullable=True, default=0)
    offer_discount = Column(Numeric(10, 2), nullable=True, default=0)
    additional_discount = Column(Numeric(10, 2), nullable=True, default=0)
    delivery_fee = Column(Numeric(10, 2), nullable=True, default=0)
    handling_fee = Column(Numeric(10, 2), nullable=True, default=0)
    tax_total = Column(Numeric(10, 2), nullable=True, default=0)
    total_amount = Column(Numeric(10, 2), nullable=False)
    order_status = Column(Enum(CartOrderStatus), nullable=False, index=True)
    is_delivery = Column(Boolean, default=False, nullable=False)
    is_online_payment = Column(Boolean, default=False, nullable=False)
    payment_mode = Column(Enum(OrderPaymentMode), nullable=False, default="offline")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="orders")
    cart = relationship("Cart", back_populates="order")
    business_contact = relationship("BusinessContact", back_populates="orders")
    created_by = relationship("User", back_populates="created_orders")

    payments = relationship("OrderPayment", back_populates="order", cascade="all, delete-orphan")
    delivery_detail = relationship("OrderDeliveryDetail", back_populates="order", uselist=False, cascade="all, delete-orphan")
    status_logs = relationship("OrderStatusLog", back_populates="order", cascade="all, delete-orphan")
    action_logs = relationship("OrderActionLog", back_populates="order", cascade="all, delete-orphan")

# order_payments table
class OrderPayment(Base):
    __tablename__ = "order_payments"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    payment_gateway = Column(String, nullable=True)
    payment_reference_id = Column(String, nullable=True)
    payment_method = Column(Enum(OrderPaymentMethod), nullable=False)
    gateway_status = Column(String, nullable=True)
    payment_status = Column(Enum(OrderPaymentStatus), nullable=False, index=True)
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(10), default="INR", nullable=False)
    gateway_fee = Column(Numeric(10,2), nullable=True)
    receipt_url = Column(String, nullable=True)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    is_manual_entry = Column(Boolean,default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    __table_args__ = (
    Index('ix_order_payments_order_id_status', 'order_id', 'payment_status'),
    )
    
    order = relationship("Order", back_populates="payments")

# order_delivery_details table
class OrderDeliveryDetail(Base):
    __tablename__ = "order_delivery_details"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    delivery_type = Column(String, nullable=False)
    address_line1 = Column(String, nullable=False)
    address_line2 = Column(String, nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    postal_code = Column(String, nullable=True)
    country = Column(String, nullable=True)
    scheduled_date = Column(Date, nullable=True)
    scheduled_time_slot = Column(String, nullable=True)
    estimated_delivery_at = Column(DateTime(timezone=True), nullable=True)
    delivery_status = Column(String, nullable=False, default='not_started', index=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    delivery_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="delivery_detail")
# order_status_logs table
class OrderStatusLog(Base):
    __tablename__ = "order_status_logs"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    from_status = Column(String, nullable=True)
    to_status = Column(String, nullable=False)
    changed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_by_role = Column(String, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="status_logs")
    changed_by = relationship("User", back_populates="order_status_changes")

# order_action_logs table
class OrderActionLog(Base):
    __tablename__ = "order_action_logs"
    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("orders.id", ondelete="CASCADE"), nullable=False, index=True)
    action_type = Column(String, nullable=False)
    reason = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    initiated_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    initiated_by_role = Column(String, nullable=False)
    amount = Column(Numeric(10, 2), nullable=False, default=0)
    status = Column(String, nullable=False)
    approved_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    order = relationship("Order", back_populates="action_logs")
    initiated_by = relationship("User", foreign_keys=[initiated_by_user_id], back_populates="initiated_order_actions")
    approved_by = relationship("User", foreign_keys=[approved_by_user_id], back_populates="approved_order_actions")