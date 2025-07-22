from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.response import ResponseHandler
from app.crud import product as crud_product
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.product import ProductCreate, ProductCustomFieldCreate, ProductCustomFieldUpdate, ProductFilters, ProductMasterDataCreate, ProductMasterDataUpdate


router = APIRouter(
    prefix="/api/admin/v1/product",
    tags=["Product"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/create-product")
def create_product(product_in: ProductCreate, request:Request ,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.create_product(db, product_in,current_user)
        return ResponseHandler.success(message= translator.t("product_created", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


@router.put("/update-product/{product_id}")
def update_product(product_id:int,request:Request ,product_in: ProductCreate, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.update_product(db,product_id ,product_in,current_user)
        return ResponseHandler.success(message= translator.t("product_updated", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/toggle-status/{status_type}/{product_id}")
def toggle_product_status(status_type:str,product_id: int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        product = crud_product.toggle_product_status(db,status_type, product_id)
        return ResponseHandler.success(message= translator.t("product_status_updated", lang), data={"id": product.id, "is_active": product.is_active})
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang),error=str(e))
    
@router.get("/get-product-details/{product_id}")
def get_product_details(product_id: int,request:Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        product = crud_product.get_product_details(db, product_id)
        if not product:
            raise ResponseHandler.not_found(message=translator.t("product_not_found", lang))
        return ResponseHandler.success(data=jsonable_encoder(product))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))

@router.post("/get-product-list")
def get_product_list(request: Request,filters:ProductFilters,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        total, items = crud_product.get_product_list(db, filters,current_user)
        if not items:
            return ResponseHandler.not_found(message=translator.t("products_not_found", lang))
        return ResponseHandler.success(data={"total":total, "items": jsonable_encoder(items)})
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
    

# Master Data APIs
@router.post("/create-master-data")
def create_master_data(payload: ProductMasterDataCreate, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.create_master_data(db, payload,current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))


@router.get("/get-master-data")
def get_master_data(request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.get_master_data_list(db,current_user)
        return ResponseHandler.success(data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))


@router.post("/update-master-data")
def update_master_data(payload: ProductMasterDataUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.update_master_data(db,payload)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))


# Custom Field APIs 
@router.post("/create-custom-field")
def create_custom_field(payload: ProductCustomFieldCreate, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.create_custom_field(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/get-custom-fields")
def get_custom_fields(request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.get_custom_field_list(db, current_user)
        return ResponseHandler.success(data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/update-custom-field")
def update_custom_field(payload: ProductCustomFieldUpdate, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.update_custom_field(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/delete-custom-field/{custom_field_id}")
def delete_custom_field(custom_field_id: int, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_product.delete_custom_field(db, custom_field_id, current_user)
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang), data={"id": data.id})
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
