# models/product.py
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, CheckConstraint,
    Numeric, Boolean, TIMESTAMP, UniqueConstraint,DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class Service(Base):
    __tablename__ = 'services'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    subcategory_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    description = Column(String(1000), nullable=False)
    price = Column(Numeric,nullable=False)
    discount_type = Column(String, nullable=True)  # e.g. "percentage", "flat"
    discount_value = Column(Numeric, nullable=True)  # e.g. 10 for 10% or 100 for flat $100 off
    
    include_tax = Column(Boolean, default=False) # if True, add tax in amount
    tax_value = Column(Numeric, nullable=True) # if include_tax is True, this is the tax value in %
    
    additional_fees = Column(JSONB, nullable=True) # e.g. {"fee_name": "fee_value", ...}
    # Specifies where the service is provided: onsite (at business), online (virtual), or at the customer's location.
    location_type = Column(String, nullable=True, comment="Service location type: 'onsite', 'online', or 'customer_location'.")

    # The maximum number of participants allowed per booking (useful for group services or classes).
    capacity = Column(Integer, nullable=True, comment="Maximum number of people per booking (group services/classes).")

    # Indicates if advance booking is required (True), or if walk-ins are allowed (False).
    booking_required = Column(Boolean, default=True, comment="True if booking is required; False allows walk-ins.")

    # Flexible JSON field for storing additional, business-specific service properties without changing the schema.
    custom_fields = Column(JSONB, nullable=True, comment="Custom, business-specific fields (flexible JSON).")
    tags = Column(JSONB, nullable=True) # Searching Tags 

    duration_minutes = Column(Integer,nullable = True) # duration of service in minutes Ex- Yoga (60) , Haircut (30)
    cancellation_policy = Column(String(1000), nullable=True) # Ex- 24 hours prior to service start time
    
    is_featured = Column(Boolean, default=False) #For featured services
    is_active = Column(Boolean,nullable=False)
    is_deleted = Column(Boolean, nullable=False, default=False)
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    # Explicit relationships
    main_service_category = relationship("Category", foreign_keys=[category_id], back_populates="main_services")
    sub_service_category = relationship("Category", foreign_keys=[subcategory_id], back_populates="sub_services")
    businesses = relationship("Business", back_populates="services")
    medias = relationship("ServiceMedia",back_populates="services",uselist=False, cascade="all, delete-orphan")
    schedules = relationship("ServiceSchedule",back_populates="services",uselist=False, cascade="all, delete-orphan")

class ServiceSchedule(Base):
    __tablename__ = "service_schedules"

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey("services.id", ondelete="CASCADE"))

    schedule_type = Column(String, nullable=False)  # "time_slot", "duration", "date_range","fixed","flexible"

    # Used for 'time_slot' like barber or coaching
    days_of_week = Column(JSONB, nullable=True)  # e.g. ["Monday", "Wednesday"]
    start_time = Column(String, nullable=True)   # e.g. "17:00"
    end_time = Column(String, nullable=True)     # e.g. "18:00"

    # Used for 'duration' like "5 days 4 nights"
    duration_days = Column(Integer, nullable=True)
    duration_nights = Column(Integer, nullable=True)

    # Used for exact schedules (e.g. tour dates)
    start_date = Column(DateTime(timezone=True), nullable=True)
    end_date = Column(DateTime(timezone=True), nullable=True)

    # Number of minutes before the service starts, reserved for setup or preparation.
    buffer_time_before = Column(Integer, nullable=True, comment="Minutes before service for setup/preparation.")

    # Number of minutes after the service ends, reserved for cleanup or transition.
    buffer_time_after = Column(Integer, nullable=True, comment="Minutes after service for cleanup/transition.")

    # Minimum number of minutes in advance that a booking must be made.
    lead_time = Column(Integer, nullable=True, comment="Minimum advance time (in minutes) required for booking.")

    # Indicates whether the service schedule is recurring (e.g., weekly class).
    recurring = Column(Boolean, default=False, comment="True if the schedule repeats regularly (recurring).")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    services = relationship("Service", back_populates="schedules")


class ServiceMedia(Base):
    __tablename__ = 'service_medias'

    id = Column(Integer, primary_key=True, index=True)
    service_id = Column(Integer, ForeignKey('services.id'), nullable=False)
    media_url = Column(Text, nullable=False)
    media_type = Column(String,nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    services = relationship("Service", back_populates="medias")
