from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordRequestForm
from app.helpers.utils import get_lang_from_request
from app.models.enums import OtpTypeEnum, PlanStatus
from app.models.plan import Plan
from app.schemas.user import SendOtp, UserCreate, ForgetPassword, ResetPassword, UserUpdate, VerifyOtp
from app.crud import user as crud_user
from app.crud import business as crud_business
from app.db.session import get_db
from app.core.security import *
from app.services.messaging import gupshup as gupshup
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

@router.post("/send-otp")
def send_otp(request: Request, payload: SendOtp, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = None  # Default if no user_id provided
        if payload.user_id:
            user = crud_user.get_user_by_id(db, payload.user_id)
            if not user:
                return ResponseHandler.bad_request(message=translator.t("user_not_found", lang))
            else:
                payload.isd_code = user.isd_code
                payload.phone_number = user.phone_number
        
        if not payload.user_id and payload.phone_number:
            user = crud_user.get_user_by_email_or_phone(db, payload.phone_number)
            if user:
                access_token = create_access_token(data={"sub": str(user.id)})
                if user.is_active and user.business.is_active:
                    return ResponseHandler.success(
                        data={"access_token": access_token, "token_type": "bearer","user":jsonable_encoder(user)},
                        message=translator.t("username_exists", lang),
                        code=201
                    )
                if user.is_active and not user.business.is_active:
                    return ResponseHandler.success(
                        data={"access_token": access_token, "token_type": "bearer","user":jsonable_encoder(user)},
                        message=translator.t("username_exists", lang),
                        code=202
                    )
                elif not user.is_active and not user.business.is_active:
                    return ResponseHandler.success(
                        data={"access_token": access_token, "token_type": "bearer","user":jsonable_encoder(user)},
                        message=translator.t("username_exists", lang),
                        code=203
                    )

        new_otp = crud_user.create_otp_for_user(db=db,otp_type=payload.otp_type,user=user,isd_code=payload.isd_code,phone_number=payload.phone_number)
        
        sent_otp = gupshup.send_whatsapp_otp_gupshup(payload.isd_code,payload.phone_number,new_otp)
        crud_user.mark_otp_as_sent(db, new_otp)
        # if sent_otp:
        #     crud_user.mark_otp_as_sent(db, new_otp)
        # else:
        #     crud_user.mark_otp_as_sent(db, new_otp) 
        #     logger.error(f"Failed to send OTP via WhatsApp to {payload.isd_code}{payload.phone_number}")
        #     return ResponseHandler.bad_request(message=translator.t("otp_sent_failed", lang))
        return ResponseHandler.success(
            message=translator.t("otp_resent", lang),
            data={"user_id": new_otp.user_id}
        )
    except Exception as e:
        logger.exception("Send Otp Failed ", exc_info=e)
        return ResponseHandler.bad_request(message=translator.t("otp_resend_failed", lang), error=str(e))

@router.post("/verify-otp")
def verify_otp(payload: VerifyOtp, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        # 1️⃣ Verify OTP
        otp_entry = crud_user.verify_otp(db=db, payload=payload)

        # 2️⃣ Handle based on OTP type
        user = None
        if otp_entry.user_id:
            user = db.query(crud_user.User).filter(crud_user.User.id == otp_entry.user_id).first()

            if not user and  payload.otp_type in [OtpTypeEnum.Login,OtpTypeEnum.ForgetPassword,OtpTypeEnum.ResetPassword,OtpTypeEnum.UpdatePhone]:
                return ResponseHandler.bad_request(
                    message=translator.t("user_not_found", lang)
                )

        return ResponseHandler.success(
            data=jsonable_encoder(otp_entry),
            message=translator.t("otp_verified_success", lang)
        )

    except Exception as e:
        logger.exception("Verify OTP failed", exc_info=e)
        return ResponseHandler.bad_request(
            message=translator.t(str(e), lang),
            error=str(e)
        )

@router.post("/login")
def login_user(request: Request,form_data: OAuth2PasswordRequestForm = Depends(),db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        user = crud_user.get_user_by_username(db,form_data.username)
        if not user or not (verify_username_password(form_data.password, user.password)):
            return ResponseHandler.unauthorized(message=translator.t("invalid_credentials", lang))
        
        access_token = create_access_token(data={"sub": str(user.id)})
        # Case: User active, business active, but no active plan
        if (
            user.is_active 
            and user.business.is_active 
            and (
                not user.plans 
                or not any(plan.status == PlanStatus.ACTIVE for plan in user.plans)
            )
        ):
            return ResponseHandler.success(
                data={
                    "access_token": access_token,
                    "token_type": "bearer",
                    "user": jsonable_encoder(user)
                },
                message=translator.t("username_exists", lang),
                code=204
            )

        # Case: User active, business active, no plans at all
        elif user.is_active and user.business.is_active and (
                user.plans 
                and any(plan.status == PlanStatus.ACTIVE for plan in user.plans)
            ):
            return ResponseHandler.success(
                data={"access_token": access_token, "token_type": "bearer", "user": jsonable_encoder(user)},
                message=translator.t("username_exists", lang),
                code=201
            )

        # Case: User active, business inactive, no plans
        elif user.is_active and not user.business.is_active and not user.plans:
            return ResponseHandler.success(
                data={"access_token": access_token, "token_type": "bearer", "user": jsonable_encoder(user)},
                message=translator.t("username_exists", lang),
                code=202
            )

        # Case: User inactive, business inactive, no plans
        elif not user.is_active and not user.business.is_active and not user.plans:
            return ResponseHandler.success(
                data={"access_token": access_token, "token_type": "bearer", "user": jsonable_encoder(user)},
                message=translator.t("username_exists", lang),
                code=203
            )

        return ResponseHandler.success(
            data={"access_token": access_token, "token_type": "bearer","user":jsonable_encoder(user)},
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

        new_otp = crud_user.create_otp_for_user(db,OtpTypeEnum.ForgetPassword, user)
        sent_otp = gupshup.send_whatsapp_otp_gupshup(user.isd_code,user.phone_number,new_otp)
        # crud_user.mark_otp_as_sent(db, new_otp)
        if sent_otp:
            crud_user.mark_otp_as_sent(db, new_otp)
        else:
            logger.error(f"Failed to send OTP via WhatsApp to {user.isd_code}{user.phone_number}")
            return ResponseHandler.bad_request(message=translator.t("otp_sent_failed", lang),)
        return ResponseHandler.success(message=translator.t("otp_sent", lang), data={"user_id": new_otp.user_id})
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("forget_password_error",lang),error=str(e))

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

@router.get("/get-plans")
def get_plans(request: Request,db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        plans = db.query(Plan).all()
        return ResponseHandler.success(message=translator.t("plans_retrieved", lang),data=jsonable_encoder(plans))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("plans_retrieval_failed", lang), error=str(e))
