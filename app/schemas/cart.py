from typing import Optional
from pydantic import BaseModel, Field
from uuid import UUID

class AddToCart(BaseModel):
    business_id:int
    business_contact_id: Optional[UUID] = None
    anonymous_id:Optional[UUID] = None
    source:str
    item_type:str
    item_id:int
    quantity:int
    date:Optional[str] = None

class GetCartRequest(BaseModel):
    business_id: int
    business_contact_id: Optional[UUID] = None
    anonymous_id:Optional[UUID] = None
    user_id:Optional[int] = None

class AssignCartContact(BaseModel):
    cart_id:int
    business_contact_id:Optional[UUID] = None
    phone_number:Optional[str] = None
    isd_code:Optional[str] = None

class CartEntities(BaseModel):
    search:Optional[str] = None
    business_type:Optional[str] = None
    is_products:Optional[bool] = False
    is_services:Optional[bool] = False
    is_combos:Optional[bool] = False
    category_id:Optional[str] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'