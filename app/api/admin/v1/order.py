from typing import Optional
from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import order as crud_order
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.cart import AddToCart, AssignCartContact, CartEntities, GetCartRequest
from app.schemas.faq import *
from app.schemas.order import OrderListFilters, OrderStatusUpdateRequest, PayNowRequest, PlaceOrderRequest

router = APIRouter(
    prefix="/api/admin/v1/order",
    tags=["Order"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/get-entities")
def get_entities(payload:CartEntities,request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.get_entities(db,payload,current_user)
        return ResponseHandler.success(message=translator.t("entities_retrieved", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/add-to-cart")
def add_to_cart(payload: AddToCart, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.add_to_cart(db,payload,current_user)
        return ResponseHandler.success(message=translator.t("added_in_cart", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.post("/update-cart-item/{cart_item_id}/{quantity}")
def update_cart_item(cart_item_id:int,quantity:int, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.update_cart_item(db,cart_item_id=cart_item_id,quantity=quantity)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.delete("/remove-cart-item/{cart_item_id}")
def remove_cart_item(cart_item_id:int, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.remove_cart_item(db,cart_item_id=cart_item_id)
        return ResponseHandler.success(message=translator.t("removed", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.delete("/delete-cart/{cart_id}")
def delete_cart(cart_id:int, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.delete_cart(db,cart_id=cart_id)
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-cart")
def get_cart(payload:GetCartRequest, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.get_cart(db,payload.business_id,payload.business_contact_id,payload.anonymous_id,payload.user_id)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/apply-coupon/{cart_id}/{coupon_code}")
def apply_coupon(cart_id:int,coupon_code:str, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.apply_coupon(db,cart_id,coupon_code)
        return ResponseHandler.success(message=translator.t("coupon_applied", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.delete("/remove-coupon/{cart_id}")
def remove_coupon(cart_id:int, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.remove_coupon(db,cart_id)
        return ResponseHandler.success(message=translator.t("coupon_removed", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/assign-cart-contact")
def assign_cart_contact(payload:AssignCartContact, request: Request, db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.assign_cart_contact(db,payload,current_user)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
 
@router.post("/checkout/{cart_id}/{additional_discount}")
def checkout_order(cart_id: int, request: Request,additional_discount:Optional[float] = 0, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.checkout_order(db, cart_id, additional_discount,current_user)
        return ResponseHandler.success(message=translator.t("order_checked_out", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/pay-now")
def pay_now(payload_list: List[PayNowRequest], request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.pay_now(db, payload_list,current_user)
        return ResponseHandler.success(message=translator.t("payment_successful", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/place-order")
def place_order(payload: PlaceOrderRequest, request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.place_order(db, payload,current_user)
        return ResponseHandler.success(message=translator.t("order_placed", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/update-order-status")
def update_order_status_manually(payload: OrderStatusUpdateRequest, request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.update_order_status_manually(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("order_status_updated", lang), data=data)
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-order-list")
def get_orders(payload:OrderListFilters,request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.get_orders(db,payload,current_user)
        return ResponseHandler.success(message=translator.t("order_statuses_retrieved", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/get-order-details")
def get_order_details(order_id:int,request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.get_order_details(db,order_id=order_id)
        return ResponseHandler.success(message=translator.t("order_statuses_retrieved", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/create-invoices/{order_id}/{is_all_order}")
def create_invoices(request: Request, order_id:Optional[int] = None, is_all_order:Optional[bool] = False ,db: Session = Depends(get_db),current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_order.create_invoices(db,order_id,is_all_order,current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=jsonable_encoder(data))
    except ValueError as e:
        return ResponseHandler.bad_request(message=str(e))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )