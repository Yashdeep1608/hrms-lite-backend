from fastapi import APIRouter, Depends, Query, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder # type: ignore
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import service as crud_service
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.service import ServiceCreate, ServiceFilter, ServiceUpdate

router = APIRouter(
    prefix="/api/admin/v1/service",
    tags=["Service"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.post("/create-service")
def create_service(service_in: ServiceCreate, request:Request ,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_service.create_service(db, service_in,current_user=current_user)
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
    
@router.get("/get-service-details/{service_id}")
def get_service_details(service_id: int,request:Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        service = crud_service.get_service_details(db, service_id)
        return ResponseHandler.success(data=jsonable_encoder(service))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang),error=str(e))

@router.post("/get-service-list")
def get_service_list(filters: ServiceFilter,request: Request,db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        total, items = crud_service.get_service_list(db, filters,current_user)
        return ResponseHandler.success(data={"total": total, "items": jsonable_encoder(items)})  # type: ignore
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/service-dropdown")
def get_service_dropdown(request: Request,is_parent: bool = Query(False),search: str=Query(None),db: Session = Depends(get_db),current_user = Depends(get_current_user)
):
    lang = get_lang_from_request(request)

    try:
        data = crud_service.get_service_dropdown(db,is_parent,search, current_user)
        return ResponseHandler.success(data=jsonable_encoder(data))

    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )