from typing import Optional
from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import faq as crud_faq
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.faq import *

router = APIRouter(
    prefix="/api/admin/v1/faq",
    tags=["FAQ"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

# 👉 Create FAQ
@router.post("/create")
def create_faq(faq_in: FAQCreateSchema, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_faq.create_faq(db, faq_in)
        return ResponseHandler.success(message=translator.t("faq_created", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# 👉 Update FAQ
@router.put("/update/{faq_id}")
def update_faq(faq_id: int, faq_in: FAQUpdateSchema, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_faq.update_faq(db, faq_id, faq_in)
        return ResponseHandler.success(message=translator.t("faq_updated", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# 👉 List FAQs (optionally filter by business_id)
@router.get("/list")
def get_faqs(request: Request, business_id: Optional[int] = None, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_faq.get_faqs(db, business_id=business_id)
        return ResponseHandler.success(message=translator.t("faqs_retrieved", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# 👉 Get one FAQ by ID
@router.get("/get/{faq_id}")
def get_faq(faq_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_faq.get_faq_by_id(db, faq_id)
        return ResponseHandler.success(message=translator.t("faq_retrieved", lang), data=data)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# 👉 Delete FAQ by ID
@router.delete("/delete/{faq_id}")
def delete_faq(faq_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_faq.delete_faq(db, faq_id)
        return ResponseHandler.success(message=translator.t("faq_deleted", lang))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )