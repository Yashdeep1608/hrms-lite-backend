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
from app.models.enums import RoleTypeEnum
from app.models.user import UserTourProgress
from app.schemas.user import ChangePassword, CreateDownlineUser, UserUpdate, UserOut
from app.services.payments.razorpay_service import *
from fastapi.encoders import jsonable_encoder

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
        return ResponseHandler.success(data=jsonable_encoder(data))
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
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.put("/{user_id}")
def update_user(user_id: int, data: UserUpdate, request: Request, db: Session = Depends(get_db)):
   lang = get_lang_from_request(request)
   try:
       updated_user = crud_user.update_user(db, user_id, data)
       return ResponseHandler.success(data=UserOut.model_validate(updated_user).model_dump(mode="json"),
                                      message=translator.t("user_updated", lang))
   except Exception as  e:
       return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.post("/upload")
def upload_image(request:Request,file: UploadFile = File(...)):
    lang = get_lang_from_request(request)
    try:
        file_url = upload_file_to_s3(file)
        return ResponseHandler.success(data={"url": file_url})
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.post("/change-password")
def change_password(
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
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))

@router.get("/get-platform-users")
def get_platform_users(request: Request, db: Session = Depends(get_db),current_user: User = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        users = crud_user.get_platform_user_list(db,current_user)
        return ResponseHandler.success(data=jsonable_encoder(users))
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.post("/create-downline-user")
def create_downline_user(
    payload: CreateDownlineUser,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lang = get_lang_from_request(request)

    try:
        # Only Superadmin, Platform Admin, or Admin can create downline users
        if current_user.role not in [RoleTypeEnum.SUPERADMIN,RoleTypeEnum.ADMIN,RoleTypeEnum.PLATFORM_ADMIN]:
            raise ResponseHandler.unauthorized(code=403, message=translator.t("unauthorized", lang))

        # Prevent creation of other admins unless current user is Superadmin
        if payload.role in [RoleTypeEnum.PLATFORM_ADMIN, RoleTypeEnum.ADMIN] and current_user.role != RoleTypeEnum.SUPERADMIN:
            raise ResponseHandler.unauthorized(code=403, message=translator.t("unauthorized", lang))

        new_user = crud_user.create_downline_user(db, payload, current_user)

        return ResponseHandler.success(
            message=translator.t("user_created_successfully", lang),
            data=jsonable_encoder(new_user)
        )
    except Exception as e:
        return ResponseHandler.internal_error(message=translator.t("something_went_wrong", lang), error=str(e))
    
@router.get("/tours/pending")
def get_pending_tours(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    try:
        completed_tours = [
            tour_key for (tour_key,) in db.query(UserTourProgress.tour_key)
            .filter(
                UserTourProgress.user_id == current_user.id,
                UserTourProgress.completed == True
            )
            .all()
        ]

        return ResponseHandler.success(data=completed_tours)
    except Exception as e:
        return ResponseHandler.internal_error(error=str(e))

@router.post("/tours/complete/{tour_key}")
def complete_tour(tour_key: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    tour = (
        db.query(UserTourProgress)
        .filter(UserTourProgress.user_id == current_user.id, UserTourProgress.tour_key == tour_key)
        .first()
    )
    if not tour:
        tour = UserTourProgress(user_id=current_user.id, tour_key=tour_key, completed=True)
        db.add(tour)
    else:
        tour.completed = True
    db.commit()
    return ResponseHandler.success(data=True)
