from fastapi import APIRouter, Depends, Form, Request
from sqlalchemy.orm import Session
from app.helpers.utils import get_lang_from_request
from app.models.enums import OtpTypeEnum, RoleTypeEnum
from app.schemas.user import SendOtp, ForgetPassword, ResetPassword, VerifyOtp
from app.crud import user as crud_user
from app.db.session import get_db
from app.core.security import *
from app.helpers.response import ResponseHandler  # import your custom response handler
from app.helpers.translator import Translator
from fastapi.encoders import jsonable_encoder # type: ignore

import logging
logger = logging.getLogger(__name__)

translator = Translator()

router = APIRouter(
    prefix="/api/admin/v1/auth",
    tags=["Authentication"]
)
class LoginForm:
    def __init__(self,password: str = Form(...), phone_number: str = Form(None)):
        self.password = password
        self.phone_number = phone_number

@router.post("/login")
def login_user(
    request: Request,
    form_data: LoginForm = Depends(),
    db: Session = Depends(get_db)
):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_email_or_phone(db, form_data.phone_number)
        if not user or not (verify_username_password(form_data.password, user.password)):
            return ResponseHandler.unauthorized(message=translator.t("invalid_credentials", lang))

        access_token = create_access_token(data={"sub": str(user.id)})

        # Case 4: User inactive
        if not user.is_active:
            return ResponseHandler.success(
                data={"access_token": access_token, "token_type": "bearer", "user": jsonable_encoder(user)},
                message=translator.t("user_exists", lang),
                code=203
            )

        # Default case
        return ResponseHandler.success(
            data={"access_token": access_token, "token_type": "bearer", "user": jsonable_encoder(user)},
            message=translator.t("login_success", lang)
        )

    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("login_failed", lang), error=str(e))
