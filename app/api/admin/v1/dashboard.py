from datetime import timezone
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
from app.models.motivation import DailyMotivation
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

@router.get("/expense-summary")
def get_expense_summary(request: Request,db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = dashboard.get_expense_summary(db, current_user.business_id)
        return ResponseHandler.success(data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/finance-summary")
def get_finance_summary(request: Request,db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        ledger_stats = dashboard.get_ledger_stats(db, current_user.business_id)
        loan_stats = dashboard.get_loans_stats(db, current_user.business_id)
        supply_stats = dashboard.get_supplier_stats(db, current_user.business_id)
        return ResponseHandler.success(data={
            "loans": jsonable_encoder(loan_stats),
            "ledgers": jsonable_encoder(ledger_stats),
            "suppliers": jsonable_encoder(supply_stats)
        })
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/loan-repayment-reminder")
def get_loan_repayment_reminders(request: Request,db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        # Loan reminders
        loan_data = dashboard.get_loan_repayment_reminders(db, current_user)

        # Daily motivation
        today = datetime.now(timezone.utc).date()
        motivation = db.query(DailyMotivation).filter(DailyMotivation.date == today).first()
        if motivation:
            quote = motivation.quote_en if lang == "en" else motivation.quote_hi
        else:
            quote = None  # fallback or leave empty

        return ResponseHandler.success(data={
            "loan_reminders": loan_data,
            "daily_motivation": quote
        })
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )