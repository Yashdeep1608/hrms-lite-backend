from typing import Optional
from fastapi import APIRouter, Depends, Query, Request, HTTPException, Path
from sqlalchemy.orm import Session
from app.core.dependencies import get_current_user
from app.db.session import get_db
from app.helpers.response import ResponseHandler
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.models.enums import RoleTypeEnum
from app.models.user import User
from app.schemas.support import (
    TicketCreate, TicketFilters, TicketMessageCreate, TicketAssignment,
    TicketPriorityChange, TicketStatusChange, TicketUpdate
)
from app.crud import support as crud_support
from fastapi.encoders import jsonable_encoder

router = APIRouter(
    prefix="/api/admin/v1/support",
    tags=["Support"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

# ------------------------
# User: Create Ticket
# ------------------------
@router.post("/create-ticket")
def create_ticket(
    payload: TicketCreate,
    request:Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        ticket = crud_support.create_user_ticket(db=db, user=current_user, payload=payload)
        return ResponseHandler.success(message=translator.t("ticket_created", lang), data=jsonable_encoder(ticket.id))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

# ------------------------
# User: List own tickets
# ------------------------
@router.post("/get-user-tickets")
def list_user_tickets(
    request: Request,
    payload: TicketFilters,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        tickets = crud_support.get_user_tickets(
            db=db,
            user=current_user,
            payload=payload
        )
        return ResponseHandler.success(data=jsonable_encoder(tickets))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

# ------------------------
# User: Get ticket thread
# ------------------------
@router.get("/get-ticket-thread")
def get_ticket_thread(
    ticket_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        ticket = crud_support.get_ticket_thread(db,ticket_id,current_user)
        return ResponseHandler.success(data=jsonable_encoder(ticket))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

# ------------------------
# User: Add reply message
# ------------------------
@router.post("/add-reply/{ticket_id}")
def add_ticket_message(
    ticket_id: int,
    request: Request,
    payload: TicketMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    lang = get_lang_from_request(request)
    try:
        message  = crud_support.add_ticket_message(db,ticket_id,current_user,payload)
        return ResponseHandler.success(data=jsonable_encoder(message))
    except Exception as e:
        return ResponseHandler.bad_request(message=translator.t("something_went_wrong", lang), error=str(e))

#------------------------------
# Get all tickets 
#------------------------------
@router.post("/get-all-tickets")
def get_all_tickets(
    payload: TicketFilters,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lang = get_lang_from_request(request)
    try:
        is_super = current_user.role in [RoleTypeEnum.SUPERADMIN, RoleTypeEnum.ADMIN]

        tickets, total = crud_support.get_all_tickets(
            db=db,
            user=current_user,
            is_superadmin=is_super,
            filters=payload
        )

        return ResponseHandler.success(
            message=translator.t("tickets_retrieved", lang),
            data={
                "items": jsonable_encoder(tickets),
                "total": total
            }
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang), error=str(e)
        )

# ------------------------
# Admin: Change Status
# ------------------------
@router.put("/update-ticket")
def update_ticket(
    request: Request,
    payload:TicketUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    lang = get_lang_from_request(request)

    try:
        is_super = current_user.role in [RoleTypeEnum.SUPERADMIN, RoleTypeEnum.PLATFORM_ADMIN]
        if not is_super:
            raise ResponseHandler.unauthorized(code=403, message=translator.t("unauthorized", lang))

        updated_ticket = crud_support.update_ticket(db=db,payload=payload,current_user=current_user)

        return ResponseHandler.success(
            message=translator.t("ticket_assigned_success", lang),
            data=jsonable_encoder(updated_ticket)
        )
    except Exception as e:
        return ResponseHandler.bad_request(
            message=translator.t("something_went_wrong", lang), error=str(e)
        )
