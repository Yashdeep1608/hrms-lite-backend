from datetime import date
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field
from uuid import UUID
from decimal import Decimal

class AddToCart(BaseModel):
    business_id:int
    business_contact_id: Optional[UUID] = None
    anonymous_id:Optional[UUID] = None
    source:str
    item_type:str
    item_id:int
    quantity:int
    time_slot:Optional[str] = None
    start_date:Optional[str] = None
    day:Optional[str] = None