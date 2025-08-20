from fastapi import APIRouter, Depends, Request, Response, status
from sqlalchemy.orm import Session
import asyncio
import logging

from app.db.session import get_db
from app.helpers.response import ResponseHandler
from app.models.webhook import WebhookMessage

# Assume these are defined in your project and imported properly:
# - crud_webhook with save_webhook_event(db, event_data)
# - ResponseHandler with success, bad_request methods
# - get_db dependency for DB session
# - translator with t method for localization
# - get_lang_from_request function

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/webhook",
    tags=["Webhook"]
)

@router.post("/whatsapp")
async def receive_webhook(request:Request,db: Session = Depends(get_db)):
    try:
        body = await request.json()

        # Acknowledge reception immediately by scheduling async DB save
        asyncio.create_task(process_webhook_event(body, db))

        # Return HTTP 200 with empty body quickly to acknowledge webhook
        return Response(status_code=status.HTTP_200_OK)

    except Exception as e:
        logger.exception("Webhook processing failed", exc_info=e)
        return ResponseHandler.bad_request(
            error=str(e)
        )

async def process_webhook_event(event_data: dict, db: Session):
    # Save the webhook event data to the database asynchronously
    try:
        event_type = event_data.get("event")  # Adjust key as per your payload

        new_event = WebhookMessage(
            event_type=event_type,
            payload=event_data
        )
        db.add(new_event)
        await db.commit()
        await db.refresh(new_event)
        return new_event
    except Exception as e:
        logger.error(f"Failed to save webhook data: {e}", exc_info=True)
