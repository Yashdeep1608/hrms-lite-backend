from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.response import ResponseHandler
from app.crud import product as crud_product
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.product import ProductCreate, ProductListOut, ProductListResponse, ProductUpdate, ProductOut


router = APIRouter(
    prefix="/api/admin/v1/product",
    tags=["Product"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/create-product", response_model=ProductOut)
def create_product(product_in: ProductCreate, request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.create_product(db, product_in)
        return ResponseHandler.success(message= translator.t("product_created", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


@router.put("/update-product", response_model=ProductOut)
def update_product(request:Request ,product_in: ProductUpdate, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.update_product(db, product_in)
        return ResponseHandler.success(message= translator.t("product_updated", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/toggle-status/{product_id}")
def toggle_product_status(product_id: int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        product = crud_product.toggle_product_status(db, product_id)
        return ResponseHandler.success(message= translator.t("product_status_updated", lang), data={"id": product.id, "is_active": product.is_active})
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang),error=str(e))
    
@router.get("/get-product-details/{product_id}", response_model=ProductOut)
def get_product_details(product_id: int,request:Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        product = crud_product.get_product_details(db, product_id)
        if not product:
            raise ResponseHandler.not_found(message=translator.t("product_not_found", lang))
        return ResponseHandler.success(data=ProductOut.model_validate(product).model_dump(mode='json'))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))

@router.get("/get-product-list/{business_id}", response_model=ProductListResponse)
def get_product_list(business_id: int,request: Request,page: int = 1,page_size: int = 20,search_text:str = '',is_active:bool = None,sort_by:str = 'created_at',sort_dir:str='desc',category_id:int = None , subcategory_id:int =None,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        total, items = crud_product.get_product_list(db, business_id, page=page, page_size=page_size,search_text=search_text,is_active=is_active,lang=lang,sort_by=sort_by,sort_dir=sort_dir, category_id=category_id,subcategory_id=subcategory_id)
        if not items:
            return ResponseHandler.not_found(message=translator.t("products_not_found", lang))
        return ResponseHandler.success(data={"total":total, "items": [ProductListOut.model_validate(p).model_dump(mode='json') for p in items]})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))


@router.post("/delete-product/{product_id}")
def toggle_product_status(product_id: int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        product = crud_product.delete_product(db, product_id)
        return ResponseHandler.success(message= translator.t("product_deleted", lang),data={"id": product.id, "is_active": product.is_active})
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang),error=str(e))