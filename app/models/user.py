from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime, Enum, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime, timezone

from app.models.enums import CreditType, OrderStatus, PaymentMode, PaymentStatus, PlanStatus

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    isd_code = Column(String(5))
    phone_number = Column(String(15), nullable = False)
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=True)  # 🔁 Moved here
    preferred_language = Column(String,default = 'en')
    parent_user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    referral_code = Column(String(16),unique=True ,nullable=False)
    referred_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)
    last_active_at = Column(DateTime)
    profile_image = Column(String,nullable=True)

    parent_user = relationship("User",remote_side=[id],foreign_keys=[parent_user_id],backref="downlines")
    business = relationship("Business", back_populates="users")
    referrer = relationship("User",remote_side=[id],foreign_keys=[referred_by],backref="referrals")
    user_otps = relationship("UserOTP", back_populates="users")
    user_permissions = relationship("UserPermission", back_populates="users")
    created_tags = relationship("Tag", back_populates="creator", cascade="all, delete-orphan")
    assigned_tags = relationship("BusinessContactTag", back_populates="user", cascade="all, delete-orphan")
    assigned_group_contacts = relationship("GroupContact", back_populates="user", cascade="all, delete-orphan")
    created_groups = relationship("Groups", back_populates="creator", cascade="all, delete-orphan")
    business_contacts_managed = relationship("BusinessContact", back_populates="managed_by_user")
    payments = relationship("UserPayment", back_populates="user")
    orders = relationship("UserOrder", back_populates="user")
    plans = relationship("UserPlan", back_populates="user")
    credits = relationship("UserCredit", back_populates="user")
    created_tickets = relationship("SupportTicket", foreign_keys="[SupportTicket.user_id]", back_populates="user")
    assigned_tickets = relationship("SupportTicket", foreign_keys="[SupportTicket.assigned_to]", back_populates="assigned_user")
    support_messages = relationship("SupportMessage", foreign_keys="[SupportMessage.sender_id]", back_populates="sender")
    ticket_logs = relationship("TicketActionLog", foreign_keys="[TicketActionLog.actor_id]", back_populates="actor")
    created_coupons = relationship("Coupon",foreign_keys="[Coupon.created_by_user_id]",back_populates="created_by")
    created_product = relationship("Product",foreign_keys="[Product.created_by_user_id]",back_populates="created_by")
    created_service = relationship("Service",foreign_keys="[Service.created_by_user_id]",back_populates="created_by")
    created_combo = relationship("Combo",foreign_keys="[Combo.created_by_user_id]",back_populates="created_by")
    created_offer = relationship("Offer",foreign_keys="[Offer.created_by_user_id]",back_populates="created_by")
    coupons = relationship("Coupon",foreign_keys="[Coupon.user_id]",back_populates="user")
    created_banners = relationship("Banner", back_populates="created_by", cascade="all, delete-orphan")
    created_carts = relationship("Cart", back_populates="created_by", cascade="all, delete-orphan")
    created_orders = relationship("Order", back_populates="created_by")
    order_status_changes = relationship("OrderStatusLog", back_populates="changed_by")
    initiated_order_actions = relationship("OrderActionLog", back_populates="initiated_by", foreign_keys="[OrderActionLog.initiated_by_user_id]")
    approved_order_actions = relationship("OrderActionLog", back_populates="approved_by", foreign_keys="[OrderActionLog.approved_by_user_id]")

class UserPayment(Base):
    __tablename__ = "user_payments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(10), default="INR")
    receipt = Column(String, nullable=False)
    razorpay_order_id = Column(String, nullable=True)
    razorpay_payment_id = Column(String, nullable=True)
    status = Column(Enum(PaymentStatus), default=PaymentStatus.CREATED)
    notes = Column(String, nullable=True)
    is_verified = Column(Boolean, default=False)
    payment_mode = Column(Enum(PaymentMode), default=PaymentMode.ONLINE)
    payment_method = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # If needed, define relationship to User
    user = relationship("User", back_populates="payments")

class UserOrder(Base):
    __tablename__ = "user_orders"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Creator of order
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)  # Optional: if tied to business
    plan_id = Column(Integer, nullable=True)
    coupon_code = Column(String, nullable=True)
    order_type = Column(String, nullable=True)  # Enum in logic: "registration", "employee_add", "feature_purchase"
    
    # pricing
    original_amount = Column(Float, nullable=False)
    offer_discount = Column(Float, default=0.0)
    coupon_discount = Column(Float, default=0.0)
    subtotal = Column(Float, nullable=False)   # after all discounts, before tax
    gst_percent = Column(Float, default=18.0)
    gst_amount = Column(Float, nullable=False)
    final_amount = Column(Float, nullable=False)

    razorpay_order_id = Column(String, nullable=True)
    status = Column(Enum(OrderStatus), default=OrderStatus.CREATED)
        
    notes = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("User", back_populates="orders")
    business = relationship("Business", back_populates="user_orders")

class UserPlan(Base):
    __tablename__ = "user_plans"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("plans.id"), nullable=False)
    payment_id = Column(UUID(as_uuid=True), ForeignKey("user_payments.id"), nullable=True)

    start_date = Column(DateTime(timezone=True), default=func.now())
    end_date = Column(DateTime(timezone=True), nullable=True)

    status = Column(Enum(PlanStatus), default=PlanStatus.PENDING)
    is_trial = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="plans")
    payment = relationship("UserPayment", backref="user_plan")
    plan = relationship("Plan", back_populates="user_plans")

class UserCredit(Base):
    __tablename__ = "user_credits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    amount = Column(Float, nullable=False)
    type = Column(Enum(CreditType), nullable=True)  # e.g. 'referral_user', 'coupon_referral'
    source_user_id = Column(Integer,nullable=False)
    code_used = Column(String(100), nullable=True)
    meta = Column(JSONB,nullable=True)
    balance_after = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    user = relationship("User", back_populates="credits")

class UserTourProgress(Base):
    __tablename__ = "user_tour_progress"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tour_key = Column(String(50), nullable=False)  # e.g., "dashboard", "team_management"
    completed = Column(Boolean, default=False)

    __table_args__ = (
        UniqueConstraint('user_id', 'tour_key', name='unique_user_tour'),
    )
