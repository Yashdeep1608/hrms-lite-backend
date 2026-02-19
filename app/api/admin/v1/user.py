from fastapi import APIRouter, Depends, Request, File, UploadFile
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.helpers.response import ResponseHandler
from app.helpers.s3 import upload_file_to_s3
from app.helpers.utils import get_lang_from_request
from app.models import User
from app.db.session import get_db
from app.helpers.translator import Translator
from app.crud import user as crud_user
from app.schemas.user import ChangePassword, UserUpdate
from fastapi.encoders import jsonable_encoder

translator = Translator()

router = APIRouter(
    prefix="/api/admin/v1/user",
    tags=["User"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/me")
def get_current_user_info(request: Request,current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        return ResponseHandler.success(data=jsonable_encoder(current_user))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
