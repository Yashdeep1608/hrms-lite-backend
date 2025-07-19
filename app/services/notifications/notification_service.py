from sqlalchemy.orm import Session
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate
from app.core.socket_manager import sio

async def send_notification(db: Session, data: NotificationCreate):
    # 1. Save to DB
    notification = Notification(
        user_id=data.user_id,
        type=data.type,
        message=data.message,
        url=data.url,
        is_read=False
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # 2. Emit to user via socket
    await sio.emit("new_notification", {
        "id": notification.id,
        "type": notification.type,
        "message": notification.message,
        "url": notification.url,
    }, room=f"user_{data.user_id}")

    return notification
