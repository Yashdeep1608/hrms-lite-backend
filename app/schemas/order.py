from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal

class PayNowRequest(BaseModel):
    order_id: int
    amount: float
    payment_method: str 
    payment_status:str
    payment_gateway: Optional[str] = None 
    gateway_reference_id: Optional[str] = None
    gateway_status:Optional[str] = None
    is_manual_entry: Optional[bool] = False             # true for manual bulk billing
class PlaceOrderRequest(BaseModel):
    order_id: int
    source: str
    is_cod_order: Optional[bool] = False

    # Optional delivery info for COD
    delivery_type: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    scheduled_date: Optional[date] = None
    scheduled_time_slot: Optional[str] = None
    delivery_notes: Optional[str] = None