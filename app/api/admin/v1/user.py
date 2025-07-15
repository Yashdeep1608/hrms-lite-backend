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
from app.schemas.user import ChangePassword, UserUpdate, UserOut
from app.services.payments.razorpay_service import *

translator = Translator()

router = APIRouter(
    prefix="/api/admin/v1/user",
    tags=["User"],
    dependencies=[Depends(get_current_user)]
)

@router.get("/me")
def get_current_user_info(request: Request,db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_user.get_user_profile_data(db, current_user)
        return ResponseHandler.success(data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/delete-user/{user_id}")
def delete_user(user_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_id(db, user_id)

        if not user:
            return ResponseHandler.bad_request(message=translator.t("user_not_found", lang))

        crud_user.soft_delete_user(db, user)
        return ResponseHandler.success(message=translator.t("user_deleted", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, request: Request, db: Session = Depends(get_db)):
   lang = get_lang_from_request(request)
   try:
       user = crud_user.get_user_by_id(db, user_id)
       if not user:
           return ResponseHandler.not_found(message=translator.t("user_not_found", lang))

       updated_user = crud_user.update_user(db, user, data)
       return ResponseHandler.success(data=UserOut.model_validate(updated_user).model_dump(mode="json"),
                                      message=translator.t("user_updated", lang))
   except Exception as  e:
       return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/upload")
async def upload_image(request:Request,file: UploadFile = File(...)):
    lang = get_lang_from_request(request)
    try:
        image_url = upload_file_to_s3(file, file.filename)
        return ResponseHandler.success(data={"url": image_url})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.post("/change-password")
async def change_password(
    payload:ChangePassword,
    request: Request,
    db: Session = Depends(get_db),
):
    lang = get_lang_from_request(request)
    try:
        updated_user = crud_user.changePassword(db,payload)
        return ResponseHandler.success(data=UserOut.model_validate(updated_user).model_dump(mode="json"),
                                      message=translator.t("password_changed", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

