from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.notification import NotificationOut
from app.models.notification import Notification
from fastapi.encoders import jsonable_encoder # type: ignore

router = APIRouter(
    prefix="/api/admin/v1/notification",
    tags=["Notification"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

@router.get("/get-notifications", response_model=list[NotificationOut])
def get_notifications(request:Request,db: Session = Depends(get_db), user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        notifications = db.query(Notification).filter(Notification.user_id == user.id).order_by(Notification.created_at.desc()).all()
        return ResponseHandler.success(data=jsonable_encoder(notifications))
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        ) 


@router.post("/mark-read/{notification_id}")
def mark_read(request:Request,notification_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        notification = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user.id).first()
        if notification:
            notification.is_read = True
            db.commit()
        return ResponseHandler.success(data=True)
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        ) 
