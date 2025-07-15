# app/services/payments/razorpay_service.py
import razorpay
from fastapi import HTTPException
from typing import Dict
from app.core.config import settings

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_order(amount: int, currency: str, receipt: str, notes: Dict):
    try:
        order = client.order.create({
            "amount": amount * 100,  # paise
            "currency": currency,
            "receipt": receipt,
            "notes": notes,
        })
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay Order Error: {str(e)}")

def verify_signature(payload: Dict):
    try:
        client.utility.verify_payment_signature(payload)
    except razorpay.errors.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid Razorpay Signature")
