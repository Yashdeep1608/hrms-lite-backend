from pydantic import BaseModel, Field
from typing import Union, List, Optional, Literal
from datetime import datetime

class OfferConditionCreate(BaseModel):
    condition_type: str
    operator: Optional[str] = Field(default="equals", pattern="^(equals|in|gte|lte)$")
    value: Union[str, int, float, List[Union[str, int]], dict]
    quantity: Optional[int] = None
    min_cart_value: Optional[float] = None

class OfferConditionUpdate(OfferConditionCreate):
    id: Optional[int]

class OfferBase(BaseModel):
    name: str
    description: Optional[str] = None
    offer_type: str
    reward_type: str
    reward_value: Union[int, float, dict, str]
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: bool = True
    auto_apply: bool = False

class OfferCreate(OfferBase):
    conditions: List[OfferConditionCreate]

class OfferUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    offer_type: Optional[str] = None
    reward_type: Optional[str] = None
    reward_value: Optional[Union[int, float, dict, str]] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: Optional[bool] = None
    auto_apply: Optional[bool] = None
    conditions: Optional[List[OfferConditionUpdate]] = None

class OfferFilters(BaseModel):
    search: Optional[str] = Field(None, description="Search by offer name")
    is_active: Optional[bool] = Field(None, description="Filter by active/inactive status")
    from_date: Optional[datetime] = Field(None, description="Start date for filtering valid_from")
    to_date: Optional[datetime] = Field(None, description="End date for filtering valid_to")
    
    sort_by: Optional[Literal["valid_from", "valid_to", "created_at", "name"]] = "valid_from"
    sort_dir: Optional[Literal["asc", "desc"]] = "asc"

    page: int = 1
    page_size: int = 20