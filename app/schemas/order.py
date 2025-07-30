from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal

class CartItemCreate(BaseModel):
    item_type: str
    item_id: int

    name: str
    actual_price: Decimal
    final_price: Decimal
    discount_price: Decimal

    quantity: Optional[int] = Field(default=1)

    # Optional service-specific fields
    time_slot: Optional[str] = None
    start_date: Optional[date] = None
    day: Optional[str] = None

class CartItemUpdate(BaseModel):
    # All fields optional on update, except probably item_id and item_type if you want to force them
    item_type: Optional[str] = None
    item_id: Optional[int] = None

    name: Optional[str] = None
    actual_price: Optional[Decimal] = None
    final_price: Optional[Decimal] = None
    discount_price: Optional[Decimal] = None

    quantity: Optional[int] = None

    time_slot: Optional[str] = None
    start_date: Optional[date] = None
    day: Optional[str] = None

class CartCreate(BaseModel):
    business_id: int
    business_contact_id: UUID
    anonymous_id: Optional[str] = None
    source: str
    created_by_user_id: Optional[int] = None

    items: Optional[List[CartItemCreate]] = []

class CartUpdate(BaseModel):
    # Since updating, all fields optional
    business_id: Optional[int] = None
    business_contact_id: Optional[UUID] = None
    anonymous_id: Optional[str] = None
    source: Optional[str] = None
    created_by_user_id: Optional[int] = None

    items: Optional[List[CartItemUpdate]] = None

