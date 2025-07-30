from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from decimal import Decimal


class ServiceBase(BaseModel):
    # Basic Info
    name: str = Field(..., max_length=100)
    description: str = Field(..., max_length=2000)
    cancellation_policy: Optional[str] = Field(default=None, max_length=1000)
    image_url: Optional[str] = None

    # Category
    category_id: int
    subcategory_path: Optional[List[int]] = None
    parent_service_id: Optional[int] = None

    # Pricing & Taxation
    price: Decimal
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    max_discount: Optional[Decimal] = None
    include_tax: Optional[bool] = False
    tax_rate: Optional[Decimal] = None

    # Service Mode
    location_type: Optional[str] = None
    is_online: Optional[bool] = False
    capacity: Optional[int] = None
    booking_required: Optional[bool] = True
    duration_minutes: Optional[int] = None

    # Schedule
    schedule_type: Optional[str] = None
    days_of_week: Optional[List[str]] = None
    start_time: Optional[str] = None  # Format: "HH:MM"
    end_time: Optional[str] = None

    duration_days: Optional[int] = None
    duration_weeks: Optional[int] = None
    duration_months: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None

    buffer_time_before: Optional[int] = None
    buffer_time_after: Optional[int] = None
    lead_time: Optional[int] = None
    recurring: Optional[bool] = False

    # Tags & Visibility
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = False
    is_active: bool = True
    is_deleted: Optional[bool] = False


class ServiceCreate(ServiceBase):
    pass


class ServiceUpdate(BaseModel):
    id:int
    name: Optional[str] = None
    description: Optional[str] = None
    cancellation_policy: Optional[str] = None
    image_url: Optional[str] = None
    category_id: Optional[int] = None
    subcategory_path: Optional[List[int]] = None
    parent_service_id: Optional[int] = None
    price: Optional[Decimal] = None
    discount_type: Optional[str] = None
    discount_value: Optional[Decimal] = None
    max_discount: Optional[Decimal] = None
    include_tax: Optional[bool] = None
    tax_rate: Optional[Decimal] = None
    location_type: Optional[str] = None
    is_online: Optional[bool] = None
    capacity: Optional[int] = None
    booking_required: Optional[bool] = None
    duration_minutes: Optional[int] = None
    schedule_type: Optional[str] = None
    days_of_week: Optional[List[str]] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_days: Optional[int] = None
    duration_weeks: Optional[int] = None
    duration_months: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    buffer_time_before: Optional[int] = None
    buffer_time_after: Optional[int] = None
    lead_time: Optional[int] = None
    recurring: Optional[bool] = None
    tags: Optional[List[str]] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None

class ServiceFilter(BaseModel):
    page: int = 1
    page_size: int = 20
    search_text: str = ''
    is_active: Optional[bool] = None
    is_online: Optional[bool] = None
    is_featured: Optional[bool] = None
    sort_by: str = 'created_at'
    sort_dir: str = 'desc'
    category_id: Optional[int] = None
