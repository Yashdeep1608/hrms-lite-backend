from typing import Optional
from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder # type: ignore
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import payment as crud_payment
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.payment import CreateOrder, PlaceOrder,RazorpayPaymentVerify
from app.services.payments.razorpay_service import verify_razorpay_signature

router = APIRouter(
    prefix="/api/admin/v1/payment",
    tags=["Payment"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()


@router.post("/create-order")
def create_order(request: Request, payload: CreateOrder, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        order = crud_payment.create_order(db, payload.order)
        return ResponseHandler.success(data= jsonable_encoder(order)),
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("create_order_failed", lang), error=str(e))
    
@router.post("/place-order")
def place_order(request: Request, payload: PlaceOrder, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        order = crud_payment.place_order(db, payload)
        return ResponseHandler.success(data= jsonable_encoder(order))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("create_order_failed", lang), error=str(e))

@router.post("/verify-payment")
def verify_payment(payload: RazorpayPaymentVerify, db: Session = Depends(get_db)):
    try:
        is_valid = verify_razorpay_signature(
            payment_id=payload.payment_id,
            order_id=payload.order_id,
            signature=payload.signature
        )
        if not is_valid:
            return ResponseHandler.bad_request(message="Invalid payment signature.")

        payment = crud_payment.verify_user_payment(db,payload)

        return ResponseHandler.success(message="Payment verified successfully.", data={"payment_id": payment.id})

    except Exception as e:
        return ResponseHandler.server_error(message="Payment verification failed.", error=str(e))