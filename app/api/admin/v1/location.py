from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.helpers.utils import get_lang_from_request
from app.db.session import get_db
from app.helpers.response import ResponseHandler  # import your custom response handler
from app.helpers.translator import Translator
from fastapi.encoders import jsonable_encoder # type: ignore

from app.models import Country, State

translator = Translator()
router = APIRouter(
    prefix="/api/admin/v1/location",
    tags=["Location"]
)
@router.get("/countries")
def get_countries(request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        countries = db.query(Country).all()
        if not countries:
            return ResponseHandler.not_found(message=translator.t("countries_not_found", lang))

        return ResponseHandler.success(
            data=jsonable_encoder(countries),
            message=translator.t("countries_retrieved", lang)
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
@router.get("/states/{country_code}")
def get_states(county_code:str,request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        states = db.query(State).filter(State.country_code == county_code).all()
        if not states:
            return ResponseHandler.not_found(message=translator.t("states_not_found", lang))

        return ResponseHandler.success(
            data=jsonable_encoder(states),
            message=translator.t("states_retrieved", lang)
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
