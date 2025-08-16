from typing import Optional
from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import dashboard as dashboard
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.faq import *

router = APIRouter(
    prefix="/api/admin/v1/dashboard",
    tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

# 👉 Get one FAQ by ID
@router.get("/product-stats")
def get_product_stats(duration_type: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = dashboard.get_dashboard_products_stats(db, current_user, duration_type)
        return ResponseHandler.success(data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/order-stats")
def get_order_stats(duration_type: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = dashboard.get_dashboard_order_stats(db, current_user, duration_type)
        return ResponseHandler.success(data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/sales-graph")
def get_sales_graph(request: Request, is_weekly:bool = False, is_daily:bool = False, is_monthly:bool = True ,db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = dashboard.get_sales_graph_data(db, current_user, is_daily=is_daily,is_monthly=is_monthly,is_weekly=is_weekly)
        return ResponseHandler.success(data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

