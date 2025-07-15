from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.core.dependencies import get_current_user
from app.helpers.utils import get_lang_from_request
from app.models.enums import OtpTypeEnum
from app.schemas.user import SendOtp, UserCreate, UserOut, ForgetPassword, ResetPassword, VerifyOtp
from app.crud import user as crud_user
from app.db.session import get_db
from app.core.security import *
from app.helpers.response import ResponseHandler  # import your custom response handler
from app.helpers.translator import Translator
from fastapi.encoders import jsonable_encoder # type: ignore

translator = Translator()

router = APIRouter(
    prefix="/api/admin/v1/auth",
    tags=["Authentication"]
)
@router.post("/register")
def register_user(user: UserCreate, request: Request,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        existing_user = crud_user.get_user_by_username(db, user.username)
        if existing_user:
            return ResponseHandler.bad_request(message=translator.t("username_exists", lang))
        
        if user.referral_code:
            referred_by_user = created_user.get_user_by_referral_code(db,user.referral_code)
            if not referred_by_user:
                return ResponseHandler.bad_request(
                    message=translator.t("referral_code_invalid", lang)
                )
            user.referred_by = referred_by_user
        
        created_user = crud_user.create_user(db, user)
        user_out = UserOut.model_validate(created_user).model_dump()

        return ResponseHandler.success(data=user_out, message=translator.t("registration_success", lang))

    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("registration_error", lang), error=str(e))

@router.post("/login")
def login_user(request: Request,form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_username(db, verify_username_password(form_data.username))
        if not user or not (verify_username_password(form_data.password, user.password)):
            return ResponseHandler.unauthorized(message=translator.t("invalid_credentials", lang))

        access_token = create_access_token(data={"sub": str(user.id)})
        return ResponseHandler.success(
            data={"access_token": access_token, "token_type": "bearer","user_id":user.id},
            message=translator.t("login_success", lang)
        )
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("login_failed", lang),error=str(e))

@router.post("/forgot-password")
def forgot_password(request: Request,payload: ForgetPassword, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_email_or_phone(db, payload.email_or_phone)

        if not user:
            return ResponseHandler.bad_request(message=translator.t("user_not_found", lang))

        user_otp = crud_user.create_otp_for_user(OtpTypeEnum.ForgetPassword, db, user)
        # send_token_email_or_sms(user.email or user.phone, token)  # Integrate your service here
        crud_user.mark_otp_as_sent(db, user_otp)
        return ResponseHandler.success(message=translator.t("otp_sent", lang), data={"user_id": user_otp.user_id})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("forget_password_error",lang),error=str(e))

@router.post("/verify-otp")
def verify_otp(payload: VerifyOtp, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        otp_entry, error_code = crud_user.verify_otp(
            db=db,
            user_id=payload.user_id,
            otp_code=payload.otp,
            otp_type=payload.otp_type
        )

        if error_code == "invalid_or_used_otp":
            return ResponseHandler.bad_request(message=translator.t("invalid_or_used_otp", lang))
        elif error_code == "otp_expired":
            return ResponseHandler.bad_request(message=translator.t("otp_expired", lang))

        return ResponseHandler.success(message=translator.t("otp_verified", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("otp_verification_failed", lang),error=str(e))

@router.post("/reset-password")
def reset_password(request: Request,payload: ResetPassword, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.reset_user_password(db, payload.user_id, payload.new_password)

        if not user:
            return ResponseHandler.bad_request(message=translator.t("invalid_or_expired_token", lang))

        return ResponseHandler.success(message=translator.t("password_reset_success", lang))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("reset_password_failed",lang),error=str(e))

@router.post("/send-otp")
def send_otp(request: Request, payload: SendOtp, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_id(db, payload.user_id)
        if not user:
            return ResponseHandler.bad_request(message=translator.t("user_not_found", lang))

        new_otp = crud_user.create_otp_for_user(payload.otp_type, db, user)
        crud_user.mark_otp_as_sent(db, new_otp)
        # Optionally send via SMS/Email

        return ResponseHandler.success(
            message=translator.t("otp_resent", lang),
            data={"user_id": new_otp.user_id}
        )
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("otp_resend_failed", lang), error=str(e))


