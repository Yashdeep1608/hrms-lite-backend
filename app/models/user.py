from enum import unique

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime, timezone

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    first_name = Column(String, nullable=False)
    last_name = Column(String, nullable=False)
    email = Column(String)
    isd_code = Column(String(5))
    phone_number = Column(String(15), nullable = False)
    whatsapp_number = Column(String(15))
    is_email_verified = Column(Boolean, default=False)
    is_phone_verified = Column(Boolean, default=False)
    username = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
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

    roles = relationship("Role", back_populates="users")
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


