# schemas/payments.py

from pydantic import BaseModel
from typing import Optional

class CreateOrder(BaseModel):
    order_type:str
    plan_id: Optional[int] = None
    coupon_code: Optional[str] = None
    extra_users:Optional[int] = None
    per_user_price:Optional[float] = None
    pro_rata_days:Optional[int] = None

class PlaceOrder(BaseModel):
    plan_id: Optional[int] = None
    coupon_code: Optional[str] = None
    order_type: Optional[str] = None  # "registration", "employee_add","upgrade or renewal" etc.

    # amounts
    original_amount: float
    offer_discount: float
    coupon_discount: float
    subtotal: float
    gst_amount: float
    final_amount: float

    # new for team members
    extra_users: Optional[int] = 0
    per_user_price: Optional[float] = 0.0
    pro_rata_days: Optional[int] = 0

    notes: Optional[str] = None
    
class RazorpayPaymentVerify(BaseModel):
    order_id: str  # Razorpay order ID
    payment_id: str  # Razorpay payment ID
    signature: str
