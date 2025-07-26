from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel


# ----------------------------
# Media Schema
# ----------------------------
class ServiceMediaCreate(BaseModel):
    media_url: str
    media_type: str
    is_primary: Optional[bool] = False

# ----------------------------
# Schedule Schema
# ----------------------------
class ServiceScheduleBase(BaseModel):
    schedule_type: Optional[str] = None 
    days_of_week: Optional[List[str]] = None     # ["Monday", "Tuesday"]
    start_time: Optional[str] = None             # "17:00"
    end_time: Optional[str] = None               # "18:00"
    duration_days: Optional[int] = None
    duration_nights: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    buffer_time_before:Optional[int] = None
    buffer_time_after:Optional[int] = None
    lead_time:Optional[int] = None
    recurring:Optional[bool] = False 


class ServiceScheduleCreate(ServiceScheduleBase):
    pass


class ServiceScheduleUpdate(ServiceScheduleBase):
    id: Optional[int]

# ----------------------------
# Service Base Schema
# ----------------------------
class ServiceBase(BaseModel):
    name: Optional[str]  = None
    business_id: Optional[int] = None
    category_id: Optional[int] = None
    subcategory_id: Optional[int] = None
    description: Optional[str]  = None
    price: Optional[float] = None
    discount_type: Optional[Literal["percentage", "flat"]] = None  
    discount_value: Optional[float] = None  
    include_tax:Optional[bool] = None
    tax_value:Optional[int] = None
    additional_fees:Optional[dict] = None
    location_type:Optional[str] = None
    capacity:Optional[int] = None
    booking_required:bool = None
    custom_fields:Optional[dict] = None
    tags:Optional[List[str]] = None
    duration_minutes:Optional[int] = None
    cancellation_policy:Optional[str] = None
    is_featured:bool = None
    is_active: bool = None
# ----------------------------
# Create / Update
# ----------------------------
class ServiceCreate(ServiceBase):
    schedules: Optional[ServiceScheduleCreate] = None
    medias: Optional[ServiceMediaCreate] = None


class ServiceUpdate(ServiceBase):
    id: int
    schedules: Optional[ServiceScheduleUpdate] = None
    medias: Optional[ServiceMediaCreate] = None
