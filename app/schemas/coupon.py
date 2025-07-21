from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date, datetime

class CouponBase(BaseModel):
    code: str = Field(..., min_length=3)
    type: str
    discount_type: str
    discount_value: float
    label: str
    description: str

    valid_from: Optional[date] = None
    valid_to: Optional[date] = None
    usage_limit: Optional[int] = None
    available_limit: Optional[int] = None
    max_discount_amount: Optional[float] = None
    min_cart_value: float = 0
    is_auto_applied: bool = False
    is_active: bool = True

    # Platform
    user_id: Optional[int] = None
    platform_target: Optional[str] = None

    # Exclusion (as JSON arrays of IDs)
    exclude_product_ids: Optional[List[int]] = []
    exclude_service_ids: Optional[List[int]] = []

class CreateCoupon(CouponBase):
    pass

class UpdateCoupon(BaseModel):
    label: Optional[str] = None
    description: Optional[str] = None
    code: Optional[str] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount_amount: Optional[float] = None
    usage_limit: Optional[int] = None
    available_limit: Optional[int] = None
    min_cart_value: Optional[float] = None
    is_auto_applied: Optional[bool] = None
    is_active: Optional[bool] = None
    
    type: Optional[str] = None
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None

    user_id: Optional[int] = None
    platform_target: Optional[str] = None

    exclude_product_ids: Optional[List[int]] = None
    exclude_service_ids: Optional[List[int]] = None

class CouponFilters(BaseModel):
    search: Optional[str] = None                        # search in code/label
    discount_type: Optional[Literal['platform', 'business']] = None
    is_active: Optional[bool] = None
    business_id: Optional[int] = None
    user_id: Optional[int] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    sort_by: Optional[str] = 'created_at'               # created_at, code, etc.
    sort_dir: Optional[Literal['asc', 'desc']] = 'desc'
    page: int = 1
    page_size: int = 10