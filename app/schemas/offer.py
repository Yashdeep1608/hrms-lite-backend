from pydantic import BaseModel, Field
from typing import Union, List, Optional, Literal
from datetime import datetime

class OfferConditionCreate(BaseModel):
    condition_type: str
    operator: Optional[str] = Field(default="equals", pattern="^(equals|in|gte|lte)$")
    value: Union[str, int, float, List[Union[str, int]], dict]
    quantity: Optional[int] = None

class OfferConditionUpdate(OfferConditionCreate):
    id: Optional[int]

class OfferBase(BaseModel):
    name: str
    description: Optional[str] = None
    offer_type: str
    reward_type: str
    reward_value: Union[int, float, dict, str]
    item_type: str
    item_id: int
    max_discount: float
    quantity: int
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: bool = True
    available_limit: int = 0
    usage_limit: int = 0
    auto_apply: bool = False
    allow_coupon: bool = False

class OfferCreate(OfferBase):
    condition: OfferConditionCreate

class OfferUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    offer_type: Optional[str] = None
    reward_type: Optional[str] = None
    reward_value: Optional[Union[int, float, dict, str]] = None
    item_type: Optional[str] = None
    item_id: Optional[int] = None
    max_discount: Optional[float] = None
    quantity: Optional[int] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    is_active: Optional[bool] = None
    usage_limit: Optional[int] = None
    available_limit: Optional[int] = None
    auto_apply: Optional[bool] = None
    allow_coupon: Optional[bool] = None
    condition: Optional[OfferConditionUpdate] = None

class OfferFilters(BaseModel):
    search: Optional[str] = Field(None, description="Search by offer name")
    is_active: Optional[bool] = Field(None, description="Filter by active/inactive status")
    from_date: Optional[datetime] = Field(None, description="Start date for filtering valid_from")
    to_date: Optional[datetime] = Field(None, description="End date for filtering valid_to")
    
    sort_by: Optional[Literal["valid_from", "valid_to", "created_at", "name"]] = "valid_from"
    sort_dir: Optional[Literal["asc", "desc"]] = "asc"

    page: int = 1
    page_size: int = 20