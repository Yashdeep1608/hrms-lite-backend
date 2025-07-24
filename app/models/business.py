from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime, timezone

class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String, nullable=False)
    business_key = Column(String,unique=True,nullable=False)
    legal_name = Column(String, nullable=True)
    business_type = Column(String,nullable=False)
    business_category = Column(Integer,nullable=False)
    registration_number = Column(String, nullable=True)
    gst_number = Column(String, nullable=True)
    pan_number = Column(String, nullable=True)
    address_line1 = Column(String,nullable=False)
    address_line2 = Column(String)
    city = Column(String, nullable=False)
    state = Column(String, nullable=False)
    country = Column(String, nullable=False)
    postal_code = Column(String,nullable=False)
    image_url = Column(String,nullable= True)
    favicon = Column(String,nullable = True)

    is_active = Column(Boolean, default=False)
    is_deleted = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="business", cascade="all, delete-orphan")  # 🔁 now correct
    categories = relationship("Category", back_populates="businesses")
    products = relationship("Product", back_populates="businesses")
    services = relationship("Service", back_populates="businesses")
    coupons = relationship("Coupon", back_populates="business")
    faqs = relationship("FAQ", back_populates="business")
    orders = relationship("UserOrder", back_populates="business", cascade="all, delete-orphan")
    tickets = relationship("SupportTicket", back_populates="business")
    combos = relationship("Combo", back_populates="business")
    offers = relationship("Offer", back_populates="business")
    banners = relationship("Banner", back_populates="business", cascade="all, delete-orphan")
