from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class CouponBase(BaseModel):
    code: str = Field(..., min_length=3)
    type: Literal["platform", "business"]
    discount_type: Literal["flat", "percentage"]
    discount_value: float

    valid_from: Optional[datetime]
    valid_to: Optional[datetime]
    usage_limit: Optional[int]
    is_active: bool = True

    # Platform
    user_id: Optional[int] = None
    platform_target: Optional[str] = None

    # Business
    business_id: Optional[int] = None

class CreateCoupon(CouponBase):
    pass

class UpdateCoupon(BaseModel):
    discount_value: Optional[float] = None
    discount_type: Optional[Literal["flat", "percentage"]] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    usage_limit: Optional[int] = None
    is_active: Optional[bool] = None
    platform_target: Optional[str] = None
    user_id: Optional[int] = None
    business_id: Optional[int] = None
