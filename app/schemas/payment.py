# schemas/payments.py

from pydantic import BaseModel
from typing import Optional

class CreateOrder(BaseModel):
    user_id: int
    plan_id: Optional[int] = None
    coupon_code: Optional[str] = None

class PlaceOrder(BaseModel):
    user_id: int
    business_id: Optional[int] = None
    plan_id: Optional[int] = None
    coupon_code: Optional[str] = None
    order_type: Optional[str] = None  # e.g., "registration", "employee_add", etc.
    original_amount:float
    offer_discount:float
    coupon_discount:float
    subtotal:float
    gst_amount:float
    final_amount:float
    notes: Optional[str] = None
    
class RazorpayPaymentVerify(BaseModel):
    user_id: int
    order_id: str  # Razorpay order ID
    payment_id: str  # Razorpay payment ID
    signature: str
