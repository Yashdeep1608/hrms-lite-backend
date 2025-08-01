# models/product.py
from datetime import datetime, timezone
from sqlalchemy import (
    ARRAY, UUID, Column, Enum, Integer, String, Text, ForeignKey,
    Numeric, Boolean,DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.enums import LocationType, ScheduleType

class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, index=True)

    # 🔹 Basic Info
    name = Column(String(100), nullable=False, comment="Service name/title")
    description = Column(String(2000), nullable=False, comment="Detailed service description")
    cancellation_policy = Column(String(1000), nullable=True, comment="Cancellation terms for the service")
    image_url = Column(Text, nullable=True, comment="Single image URL representing the service")

    # 🔹 Business Context
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False, comment="Owning business ID")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True, comment="Creator/admin user ID")

    # 🔹 Category & Parent Mapping
    parent_service_id = Column(Integer, ForeignKey("services.id"), nullable=True, comment="If this service is tied to a service (optional)")
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    subcategory_path = Column(ARRAY(Integer), nullable=True, comment="Full subcategory path as list of IDs")

    # 🔹 Pricing & Taxation
    price = Column(Numeric, nullable=False, comment="Base price of the service")
    discount_type = Column(String(20), nullable=True, comment="'percentage' or 'flat'")
    discount_value = Column(Numeric, nullable=True)
    max_discount = Column(Numeric,nullable=True)
    include_tax = Column(Boolean, default=False, comment="If true, tax is included in price")
    tax_rate = Column(Numeric, nullable=True, comment="Applicable tax rate in percentage (e.g., 18 for 18%)")

    # 🔹 Service Mode & Capacity
    location_type = Column(Enum(LocationType), nullable=True, comment="onsite | online | customer_location")
    capacity = Column(Integer, nullable=True, comment="Maximum number of participants/bookings")
    booking_required = Column(Boolean, default=True, comment="If true, booking is required")

    duration_minutes = Column(Integer, nullable=True, comment="Total duration of the service in minutes")

    # 🔹 Schedule & Availability
    schedule_type = Column(Enum(ScheduleType), nullable=True, comment="time_slot | fixed | duration | subscription | flexible")

    # For 'time_slot'/ 'fixed' schedules
    days_of_week = Column(JSONB, nullable=True, comment="Days service is available, e.g. ['Monday', 'Wednesday']")
    start_time = Column(String(10), nullable=True, comment="Start of daily slot availability/Fixed timing (e.g. '10:00')")
    end_time = Column(String(10), nullable=True, comment="End of daily slot availability/Fixed timing (e.g. '22:00')")


    # For subscriptions or duration-based services
    duration_days = Column(Integer, nullable=True)
    duration_weeks = Column(Integer, nullable=True)
    duration_months = Column(Integer, nullable=True)

    start_date = Column(DateTime(timezone=True), nullable=True, comment="Service start date")
    end_date = Column(DateTime(timezone=True), nullable=True, comment="Service end date")

    buffer_time_before = Column(Integer, nullable=True, comment="Buffer/setup time before service starts (in minutes)")
    buffer_time_after = Column(Integer, nullable=True, comment="Buffer/cleanup time after service ends (in minutes)")
    lead_time = Column(Integer, nullable=True, comment="Minimum advance time required for booking (in minutes)")

    recurring = Column(Boolean, default=False, comment="True if schedule is recurring (e.g. weekly yoga)")

    # 🔹 Tags & Visibility
    tags = Column(JSONB, nullable=True, comment="Searchable tags for discovery")
    is_featured = Column(Boolean, default=False, comment="If true, highlights this service on platform")
    is_online = Column(Boolean, default=False, comment="If true, this service shows on platform")
    is_active = Column(Boolean, nullable=False, comment="True if service is currently active")
    is_deleted = Column(Boolean, nullable=False, default=False, comment="Soft delete flag")

    # 🔹 Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # 🔹 Relationships
    businesses = relationship("Business", back_populates="services")
    service_category = relationship("Category", foreign_keys=[category_id], back_populates="services")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_service")
    parent_service = relationship("Service", remote_side=[id], backref="variants")


class ServiceBookingLog(Base):
    __tablename__ = "service_booking_logs"

    id = Column(Integer, primary_key=True)
    service_id = Column(Integer, ForeignKey("services.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
