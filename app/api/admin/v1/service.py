from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder # type: ignore
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import service as crud_service
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.service import ServiceCreate, ServiceUpdate

router = APIRouter(
    prefix="/api/admin/v1/service",
    tags=["Service"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/create-service")
def create_service(service_in: ServiceCreate, request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_service.create_service(db, service_in)
        return ResponseHandler.success(message= translator.t("service_created", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


@router.put("/update-service")
def update_service(request:Request ,service_in: ServiceUpdate, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_service.update_service(db, service_in)
        return ResponseHandler.success(message= translator.t("service_updated", lang),data=data.id)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/toggle-status/{service_id}")
def toggle_service_status(service_id: int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        service = crud_service.toggle_service_status(db, service_id)
        return ResponseHandler.success(message= translator.t("service_status_updated", lang),data={"id": service.id, "is_active": service.is_active})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))
    
@router.get("/get-service-details/{service_id}")
def get_service_details(service_id: int,request:Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        service = crud_service.get_service_details(db, service_id)
        if not service:
            raise ResponseHandler.not_found(message=translator.t("service_not_found", lang))
        return ResponseHandler.success(data=jsonable_encoder(service))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))

@router.get("/get-service-list/{business_id}")
def get_service_list(business_id: int,request: Request,page: int = 1,page_size: int = 20,search_text:str = '',is_active:bool = None,sort_by:str = 'created_at',sort_dir:str='desc',category_id:int = None , subcategory_id:int =None,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        total, items = crud_service.get_service_list(db, business_id, page=page, page_size=page_size,search_text=search_text,is_active=is_active,sort_by=sort_by,sort_dir=sort_dir,category_id=category_id,subcategory_id=subcategory_id)
        if not items:
            return ResponseHandler.not_found(message=translator.t("services_not_found", lang))
        return ResponseHandler.success(data={"total":total, "items": jsonable_encoder(items)}) # type: ignore
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))


@router.put("/delete-service/{service_id}")
def toggle_service_status(service_id: int,request:Request ,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        service = crud_service.delete_service(db, service_id)
        return ResponseHandler.success(message= translator.t("service_deleted", lang),data={"id": service.id, "is_active": service.is_active})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang),error=str(e))