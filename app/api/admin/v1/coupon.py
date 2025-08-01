from typing import Optional
from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder # type: ignore
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import coupon as crud_coupon
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.coupon import CouponFilters, CreateCoupon, UpdateCoupon

router = APIRouter(
    prefix="/api/admin/v1/coupon",
    tags=["Coupon"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/create-coupon")
def create_coupon(coupon_in: CreateCoupon, request:Request ,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_coupon.create_coupon(db, coupon_in,current_user)
        return ResponseHandler.success(message= translator.t("coupon_created", lang),data=jsonable_encoder(data.id))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.put("/update-coupon/{coupon_id}")
def update_coupon(coupon_id:int,coupon_in: UpdateCoupon, request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_coupon.update_coupon(db,coupon_id,coupon_in)
        return ResponseHandler.success(message= translator.t("coupon_updated", lang),data=jsonable_encoder(data.id))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
@router.get("/dropdown")
def get_coupon_dropdown(request: Request,db: Session = Depends(get_db),current_user = Depends(get_current_user)
):
    lang = get_lang_from_request(request)

    try:
        data = crud_coupon.get_coupon_dropdown(db, current_user)
        return ResponseHandler.success(data=jsonable_encoder(data))

    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


@router.post("/get-coupons")
def get_coupons(request:Request ,filters: CouponFilters,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_coupon.get_coupons(db,filters,current_user)
        return ResponseHandler.success(message= translator.t("coupons_retrieved", lang),data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/get-coupon/{coupon_id}")
def get_coupon_details(coupon_id:int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_coupon.get_coupon_details(db,coupon_id)
        return ResponseHandler.success(message= translator.t("coupon_retrieved", lang),data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.delete("/delete-coupon/{coupon_id}")
def delete_coupon(coupon_id:int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_coupon.delete_coupon(db,coupon_id)
        return ResponseHandler.success(message= translator.t("coupon_deleted", lang),data=True)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

