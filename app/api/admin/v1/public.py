from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
import asyncio
import logging

from app.db.session import get_db
from app.helpers.response import ResponseHandler
from app.models.learning import HowToGuide, LatestUpdate, VideoTutorial
from app.models.webhook import WebhookMessage

# Assume these are defined in your project and imported properly:
# - crud_webhook with save_webhook_event(db, event_data)
# - ResponseHandler with success, bad_request methods
# - get_db dependency for DB session
# - translator with t method for localization
# - get_lang_from_request function

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/v1/public",
    tags=["Public"]
)
# GET API for all video tutorials
@router.get("/learning/video-tutorials")
def get_video_tutorials(db: Session = Depends(get_db)):
    tutorials = db.query(VideoTutorial).all()
    return ResponseHandler.success(data=jsonable_encoder(tutorials))

# GET API for all how-to guides
@router.get("/learning/how-to-guides")
def get_how_to_guides(db: Session = Depends(get_db)):
    guides = db.query(HowToGuide).all()
    return ResponseHandler.success(data=jsonable_encoder(guides))

# GET API for all latest updates
@router.get("/learning/latest-updates")
def get_latest_updates(db: Session = Depends(get_db)):
    updates = db.query(LatestUpdate).all()
    return ResponseHandler.success(data=jsonable_encoder(updates))
