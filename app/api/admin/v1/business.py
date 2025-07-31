from typing import Optional
from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.utils import get_lang_from_request
from app.schemas.business import BusinessCreate, BusinessOut, BusinessUpdate, CategoryCreateUpdate, CategoryOut
from app.crud import business as crud_business
from app.db.session import get_db
from app.helpers.response import ResponseHandler  # import your custom response handler
from app.helpers.translator import Translator
from fastapi.encoders import jsonable_encoder # type: ignore

translator = Translator()
public_router = APIRouter(
    prefix="/api/admin/v1/business",
    tags=["Business"],
)
router = APIRouter(
    prefix="/api/admin/v1/business",
    tags=["Business"],
    dependencies=[Depends(get_current_user)]
)

@public_router.get("/business-categories")
def get_business_categories(request:Request,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        business_categories = crud_business.get_business_categories(db)
        return ResponseHandler.success(message=translator.t("categories_retrieved",lang),data=jsonable_encoder(business_categories))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@public_router.post("/register")
def register_business(business: BusinessCreate, request: Request,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        new_business = crud_business.create_business(db, business)
        return ResponseHandler.success(data=BusinessOut.model_validate(new_business).model_dump(mode="json"), message=translator.t("business_created", lang))

    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("business_registration_failed", lang), error=str(e))

@router.get("/get-category-dropdown")
def get_category_dropdown(
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        
        all_categories = crud_business.get_categories_for_dropdown(db,current_user)

        return ResponseHandler.success(data=jsonable_encoder(all_categories))

    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang), error=str(e)
        )

@router.get("/{business_id}")
def get_business_by_id(business_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        business = crud_business.get_business_by_id(db, business_id)
        if not business:
            return ResponseHandler.not_found(message=translator.t("business_not_found", lang))
        return ResponseHandler.success(data=BusinessOut.model_validate(business).model_dump(mode="json"))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/{business_key}")
def get_business_by_key(business_key: str, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        business = crud_business.get_business_by_key(db, business_key)
        if not business:
            return ResponseHandler.not_found(message=translator.t("business_not_found", lang))
        return ResponseHandler.success(data=BusinessOut.model_validate(business).model_dump(mode="json"))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/{business_id}")
def update_business(business_id: int, data: BusinessUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        business = crud_business.get_business_by_id(db, business_id)
        if not business:
            return ResponseHandler.not_found(message=translator.t("business_not_found", lang))

        updated_business = crud_business.update_business(db, business, data)
        return ResponseHandler.success(data=BusinessOut.model_validate(updated_business).model_dump(mode="json"),
                                       message=translator.t("business_updated", lang))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))


@router.delete("/{business_id}")
def deactivate_business(business_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        business = crud_business.get_business_by_id(db, business_id)
        if not business:
            return ResponseHandler.not_found(message=translator.t("business_not_found", lang))

        crud_business.deactivate_business(db, business)
        return ResponseHandler.success(message=translator.t("business_deactivated", lang))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))


@router.get("/get-categories/{business_id}")
def get_categories(
    business_id: int,
    request: Request,
    search_text: Optional[str] = '',
    is_active: Optional[bool] = None,
    parent_id: Optional[int] = None,
    sort_by: str = 'created_at',
    sort_dir: str = 'desc',
    db: Session = Depends(get_db)
):
    lang = get_lang_from_request(request)
    try:
        result = crud_business.get_categories_by_business(
            db=db,
            business_id=business_id,
            search_text=search_text,
            is_active=is_active,
            parent_id=parent_id,
            sort_by=sort_by,
            sort_dir=sort_dir
        )
        return ResponseHandler.success(data=jsonable_encoder(result))

    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


@router.post("/create-category")
def create_category(category:CategoryCreateUpdate,request:Request,db:Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        category = crud_business.create_category(db,category)
        return ResponseHandler.success(message=translator.t("category_created"))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong",lang),error=str(e))

@router.get("/get-category/{category_id}")
def get_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        category = crud_business.get_category_by_id(db, category_id)
        if not category:
            return ResponseHandler.not_found(message=translator.t("category_not_found", lang))
        return ResponseHandler.success(
            data=CategoryOut.model_validate(category).model_dump(mode="json")
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/update-category")
def update_category(data: CategoryCreateUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        category = crud_business.get_category_by_id(db, data.id)
        if not category:
            return ResponseHandler.not_found(message=translator.t("category_not_found", lang))

        updated = crud_business.update_category(db, category, data)
        return ResponseHandler.success(
            message=translator.t("category_updated", lang),
            data=CategoryOut.model_validate(updated).model_dump(mode="json")
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/toggle-category/{category_id}")
def deactivate_category(category_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        category = crud_business.get_category_by_id(db, category_id)
        if not category:
            return ResponseHandler.not_found(message=translator.t("category_not_found", lang))

        crud_business.toggle_category(db, category)
        return ResponseHandler.success(message=translator.t("category_updated", lang))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
