from datetime import datetime

from pydantic import BaseModel, EmailStr, ConfigDict
from typing import Optional, Dict

from app.models.enums import BusinessTypeEnum


class BusinessCreate(BaseModel):
    business_name:str
    legal_name:Optional[str]
    business_type:BusinessTypeEnum
    business_category:int
    registration_number:Optional[str]
    gst_number:Optional[str]
    pan_number:Optional[str]
    address_line1:str
    address_line2:Optional[str]
    city:str
    state:str
    country:str
    postal_code:str

class BusinessUpdate(BaseModel):
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    business_category:Optional[int] = None
    legal_name: Optional[str] = None
    registration_number: Optional[str] = None
    gst_number: Optional[str] = None
    pan_number: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    postal_code: Optional[str] = None
    is_active: Optional[bool] = None
    is_deleted: Optional[bool] = None
    image_url:Optional[str] = None
    favicon:Optional[str] = None

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class BusinessOut(BaseModel):
    id: int
    business_name: str
    business_type:str
    business_key: str
    business_category: int
    is_active: bool
    is_deleted: bool
    legal_name: str
    registration_number: str
    gst_number: str
    pan_number: str
    address_line1: str
    address_line2: str
    city: str
    state: str
    country: str
    postal_code: str
    image_url: Optional[str] = None
    favicon: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class CategoryCreateUpdate(BaseModel):
    id:Optional[int] = None
    name:str
    parent_id:Optional[int] = None
    business_id: int
    category_image: Optional[str] = None
    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class CategoryOut(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    business_id: int
    category_image: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")




