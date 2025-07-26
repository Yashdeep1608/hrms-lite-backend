from fastapi import APIRouter, Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.banner import BannerCreate, BannerFilters, BannerUpdate
from app.crud import marketing as crud_marketing
from app.schemas.combo import ComboCreate, ComboFilter, ComboUpdate
from app.schemas.offer import OfferCreate, OfferFilters, OfferUpdate

router = APIRouter(
    prefix="/api/admin/v1/marketing",
    tags=["Marketing"],
    dependencies=[Depends(get_current_user)]
)

translator = Translator()

#Banner APIs
@router.post("/banner/create")
def create_banner(banner_in: BannerCreate, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        banner = crud_marketing.create_banner(db, banner_in,current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=banner.id)
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/banner/list")
def list_banners(filters: BannerFilters, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        banners = crud_marketing.get_all_banners(db, filters,current_user)
        return ResponseHandler.success(data=jsonable_encoder(banners))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/banner/{banner_id}")
def get_banner(banner_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        banner = crud_marketing.get_banner(db, banner_id)
        return ResponseHandler.success(data=jsonable_encoder(banner))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/banner/{banner_id}")
def update_banner(banner_id: int, banner_in: BannerUpdate, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        updated = crud_marketing.update_banner(db, banner_id, banner_in,current_user)
        if not updated:
            return ResponseHandler.not_found(message=translator.t("banner_not_found", lang))
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=jsonable_encoder(updated))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.delete("/banner/{banner_id}")
def delete_banner(banner_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        deleted = crud_marketing.delete_banner(db, banner_id)
        if not deleted:
            return ResponseHandler.not_found(message=translator.t("banner_not_found", lang))
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))


#Combo APIs
@router.post("/combo/create")
def create_combo(
    payload: ComboCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        combo = crud_marketing.create_combo(db, payload, current_user)
        return ResponseHandler.success(
            message=translator.t("created_successfully", lang),
            data=combo.id
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/combo/{combo_id}")
def update_combo(
    combo_id: int,
    payload: ComboUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)
    try:
        combo = crud_marketing.update_combo(db, combo_id, payload)
        if not combo:
            return ResponseHandler.not_found(message=translator.t("combo_not_found", lang))
        return ResponseHandler.success(
            message=translator.t("updated_successfully", lang),
            data=True
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/combo/{combo_id}")
def delete_combo(
    combo_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)
    try:
        success = crud_marketing.delete_combo(db, combo_id)
        if not success:
            return ResponseHandler.not_found(message=translator.t("combo_not_found", lang))
        return ResponseHandler.success(
            message=translator.t("deleted_successfully", lang)
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/combo/list")
def list_combos(
    filters: ComboFilter,
    request: Request,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        result = crud_marketing.get_all_combos(db, filters, current_user)
        return ResponseHandler.success(
            data=jsonable_encoder(result)
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/combo/{combo_id}")
def get_combo(
    combo_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    lang = get_lang_from_request(request)
    try:
        combo = crud_marketing.get_combo(db, combo_id)
        if not combo:
            return ResponseHandler.not_found(message=translator.t("combo_not_found", lang))
        return ResponseHandler.success(data=jsonable_encoder(combo))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
#Offer APIs
@router.post("/offer/create")
def create_offer(payload: OfferCreate, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        offer = crud_marketing.create_offer(db, payload,current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=offer.id)
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/offer/list")
def list_offers(filters: OfferFilters, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        offers = crud_marketing.get_all_offers(db, filters,current_user,lang)
        return ResponseHandler.success(data=jsonable_encoder(offers))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/offer/{offer_id}")
def get_offer(offer_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        offer = crud_marketing.get_offer_by_id(db, offer_id)
        return ResponseHandler.success(data=jsonable_encoder(offer))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/offer/{offer_id}")
def update_offer(offer_id: int, payload: OfferUpdate, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        updated = crud_marketing.update_offer(db, offer_id, payload)
        if not updated:
            return ResponseHandler.not_found(message=translator.t("offer_not_found", lang))
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=jsonable_encoder(updated))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.delete("/offer/{offer_id}")
def delete_offer(offer_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        deleted = crud_marketing.delete_offer(db, offer_id)
        if not deleted:
            return ResponseHandler.not_found(message=translator.t("offer_not_found", lang))
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

