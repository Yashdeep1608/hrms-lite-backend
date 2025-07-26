from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Literal
from datetime import date, datetime

class ComboItemCreate(BaseModel):
    item_type: str
    item_id: int
    quantity: int = Field(gt=0)

class ComboCreate(BaseModel):
    name: Dict[str, str]  # e.g., {"en": "Pack of 2", "hi": "2 का पैक"}
    description: Optional[Dict[str, str]] = None

    combo_price: float = Field(gt=0)
    discount_type: Literal["none", "flat", "percentage"] = "none"
    discount_value: Optional[float] = None
    max_discount: Optional[float] = None

    is_active: bool = True
    is_online: bool = False
    is_featured: bool = False
    image_url: Optional[str] = None

    items: List[ComboItemCreate]

class ComboUpdate(BaseModel):
    name: Optional[Dict[str, str]] = None
    description: Optional[Dict[str, str]] = None

    combo_price: Optional[float] = None
    discount_type: Optional[Literal["none", "flat", "percentage"]] = None
    discount_value: Optional[float] = None
    max_discount: Optional[float] = None

    is_active: Optional[bool] = None
    is_online: Optional[bool] = None
    is_featured: Optional[bool] = None
    image_url: Optional[str] = None

    items: Optional[List[ComboItemCreate]] = None  # Replace all items if provided

class ComboFilter(BaseModel):
    is_active: Optional[bool] = None
    is_online: Optional[bool] = None
    is_featured: Optional[bool] = None
    search: Optional[str] = None  # Will be used to match translated `name` JSONB
    item_type: Optional[str] = None
    sort_by:Optional[str] = 'created_at'
    sort_dir:Optional[str] = 'desc'
    page:Optional[int] = 1
    page_size:Optional[int] = 20
