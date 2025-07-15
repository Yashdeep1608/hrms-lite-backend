# app/services/payments/razorpay_service.py
import razorpay
from fastapi import HTTPException
from typing import Dict
from app.core.config import settings

client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

def create_razorpay_order(amount: int, currency: str, receipt: str, notes: Dict):
    try:
        order = client.order.create({
            "amount": amount * 100,  #paise
            "currency": currency or 'INR',
            "receipt": receipt,
            "notes": notes,
        })
        return order
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Razorpay Order Error: {str(e)}")

def verify_razorpay_signature(payment_id: str, order_id: str, signature: str):
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET))
    try:
        client.utility.verify_payment_signature({
            'razorpay_order_id': order_id,
            'razorpay_payment_id': payment_id,
            'razorpay_signature': signature
        })
        return True
    except razorpay.errors.SignatureVerificationError:
        return False
    

def fetch_razorpay_payment(payment_id: str) -> dict:
    try:
        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET))
        payment = client.payment.fetch(payment_id)
        return payment
    except razorpay.errors.BadRequestError as e:
        raise Exception(f"BadRequest: {e}")
    except razorpay.errors.ServerError as e:
        raise Exception(f"ServerError: {e}")
    except Exception as e:
        raise Exception(f"Payment fetch failed: {str(e)}")

