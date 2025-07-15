from typing import List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, condecimal


# ----------------------------
# Media Schema
# ----------------------------
class ServiceMediaCreate(BaseModel):
    media_url: str
    media_type: str
    is_primary: Optional[bool] = False


class ServiceMediaOut(ServiceMediaCreate):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


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


class ServiceScheduleOut(ServiceScheduleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


# ----------------------------
# Service Base Schema
# ----------------------------
class ServiceBase(BaseModel):
    name: dict  # Multilingual name
    business_id: int
    category_id: int
    subcategory_id: Optional[int] = None  # Optional subcategory
    description: dict  # Multilingual description
    price: condecimal(max_digits=10, decimal_places=2) # type: ignore
    discount_type: Optional[Literal["percentage", "flat"]] = None  # e.g. "percentage", "flat"
    discount_value: Optional[condecimal(max_digits=10, decimal_places=2)] = None  # type: ignore # e.g. 10 for 10% or 100 for flat $100 off
    include_tax:Optional[bool] # if True, add tax in amount
    tax_value:Optional[int]
    additional_fees:Optional[dict]
    location_type:Optional[str]
    capacity:Optional[int]
    booking_required:bool
    custom_fields:Optional[dict]
    tags:Optional[List[str]]
    duration_minutes:Optional[int]
    cancellation_policy:Optional[dict]
    is_featured:bool
    is_active: bool
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


# ----------------------------
# Output Schema
# ----------------------------
class ServiceOut(ServiceBase):
    id: int
    created_at: datetime
    updated_at: datetime
    schedules: ServiceScheduleOut
    medias: ServiceMediaOut

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class ServiceListOut(BaseModel):
    id: int
    name: dict
    price: condecimal(max_digits=10, decimal_places=2)  # type: ignore
    discount_type: Optional[Literal["percentage", "flat"]] = None  # e.g. "percentage", "flat"
    discount_value: Optional[condecimal(max_digits=10, decimal_places=2)] = None  # type: ignore # e.g. 10 for 10% or 100 for flat $100 off
    is_active: bool
    service_image: Optional[str] = None  # URL of primary image
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")
class ServiceListResponse(BaseModel):
    total: int
    items: List[ServiceListOut]
