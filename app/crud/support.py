from typing import Optional
from sqlalchemy import func
from sqlalchemy.orm import Session,joinedload
from app.models.support import MessageAttachment, SupportTicket, SupportMessage, TicketAttachment
from app.models.enums import RoleTypeEnum, TicketPriority, SenderRole, TicketActionType
from app.models.user import User
from app.schemas.notification import NotificationCreate
from app.schemas.support import TicketCreate, TicketFilters, TicketMessageCreate, TicketUpdate
from datetime import datetime, timezone
from fastapi.concurrency import run_in_threadpool
import asyncio
from app.services.notifications.notification_service import send_notification


#Create Support Ticket for User 
def create_user_ticket(db: Session, user:User, payload: TicketCreate):
    # Determine priority based on premium status
    priority = TicketPriority.HIGH if payload.is_premium else TicketPriority.NORMAL

    # 1. Create the ticket
    ticket = SupportTicket(
        user_id=user.id,
        business_id=user.business_id,
        type=payload.type,
        subject=payload.subject,
        status="open",
        priority=priority,
        is_premium=payload.is_premium
    )
    db.add(ticket)
    db.flush()  # to get ticket.id

    # 2. Create initial message
    message = SupportMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        sender_role=SenderRole.USER,
        content=payload.content,
    )
    db.add(message)

    # 3. Attachments (if provided)
    for url in payload.attachments or []:
        attachment = TicketAttachment(
            ticket_id=ticket.id,
            file_url=url
        )
        db.add(attachment)

    db.commit()
    db.refresh(ticket)
    return ticket

#Get User Tickets
def get_user_tickets(
    db: Session,
    user: User,
    payload: TicketFilters,
):
    query = db.query(SupportTicket).filter(SupportTicket.user_id == user.id)

    if payload.ticket_type:
        query = query.filter(SupportTicket.type == payload.ticket_type)
    if payload.status:
        query = query.filter(SupportTicket.status == payload.status)
    if payload.search:
        search_term = f"%{payload.search.lower()}%"
        query = query.filter(SupportTicket.subject.ilike(search_term))

    sort_field = getattr(SupportTicket, payload.sort_by , SupportTicket.created_at)
    if payload.sort_dir == 'desc':
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()
    total = query.count()
    tickets = (
        query.order_by(SupportTicket.created_at.desc())
        .offset((payload.page - 1) * payload.page_size)
        .limit(payload.page_size)
        .all()
    )

    return {
        "total": total,
        "items": tickets,
    }

# Get Ticket Thread 
def get_ticket_thread(db: Session, ticket_id: int, user: User):
    messages = (
        db.query(SupportMessage)
        .options(joinedload(SupportMessage.attachments))
        .filter(SupportMessage.ticket_id == ticket_id)
        .order_by(SupportMessage.sent_at.asc())
        .all()
    )

    return [
        {
            "id": message.id,
            "ticket_id": message.ticket_id,
            "sender_id": message.sender_id,
            "sender_role": message.sender_role,
            "content": message.content,
            "sent_at": message.sent_at,
            "attachments": [
                {
                    "id": attachment.id,
                    "file_url": attachment.file_url
                }
                for attachment in message.attachments
            ]
        }
        for message in messages
    ]

# Add Reply Message
def add_ticket_message(
    db: Session,
    ticket_id: int,
    user: User,
    payload: TicketMessageCreate,
):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == ticket_id).first()

    if not ticket:
        raise Exception("Ticket not found")

    # Determine if status is changed
    create_status_log = False
    if payload.status and payload.status != ticket.status:
        ticket.status = payload.status
        create_status_log = True

    # Determine sender role for user message
    if ticket.user_id == user.id:
        sender_role = SenderRole.USER
    else:
        # platform user roles
        if user.role == RoleTypeEnum.SUPERADMIN or user.role == RoleTypeEnum.PLATFORM_ADMIN:
            sender_role = SenderRole.ADMIN
        elif user.role == RoleTypeEnum.DEVELOPER:
            sender_role = SenderRole.DEVELOPER
        elif user.role == RoleTypeEnum.SALES:
            sender_role = SenderRole.SALES
        elif user.role == RoleTypeEnum.SUPPORT:
            sender_role = SenderRole.SUPPORT
        else:
            sender_role = SenderRole.USER  # fallback for others

    # Create regular message
    message = SupportMessage(
        ticket_id=ticket.id,
        sender_id=user.id,
        sender_role=sender_role,
        content=payload.message,
    )
    db.add(message)
    db.flush()

    # Add attachments (if any)
    if payload.attachment_urls:
        for url in payload.attachment_urls:
            attachment = MessageAttachment(
                message_id=message.id,
                file_url=url
            )
            db.add(attachment)

    db.commit()
    db.refresh(message)

    # If status was changed, log it as a system message by user (not generic "system")
    if create_status_log:
        # Determine who changed the status (based on user.role)
        if user.role == RoleTypeEnum.SUPERADMIN or user.role == RoleTypeEnum.PLATFORM_ADMIN:
            sys_sender_role = SenderRole.ADMIN
        elif user.role == RoleTypeEnum.DEVELOPER:
            sys_sender_role = SenderRole.DEVELOPER
        elif user.role == RoleTypeEnum.SALES:
            sys_sender_role = SenderRole.SALES
        elif user.role == RoleTypeEnum.SUPPORT:
            sys_sender_role = SenderRole.SUPPORT
        else:
            sys_sender_role = SenderRole.USER

        status_message = SupportMessage(
            ticket_id=ticket_id,
            sender_id=user.id,
            sender_role=sys_sender_role,
            content=f"Status changed to {payload.status.upper()} by {user.first_name}"
        )
        db.add(status_message)
        db.commit()

    return message

# Get All Tickets
def get_all_tickets(
    db: Session,
    user: User,
    is_superadmin: bool,
    filters: TicketFilters
):
    query = db.query(SupportTicket).options(joinedload(SupportTicket.assigned_user))

    if not is_superadmin:
        query = query.filter(SupportTicket.assigned_to == user.id)

    if filters.search:
        search_term = f"%{filters.search.lower()}%"
        query = query.filter(func.lower(SupportTicket.subject).ilike(search_term))

    if filters.status:
        query = query.filter(SupportTicket.status == filters.status)

    if filters.ticket_type:
        query = query.filter(SupportTicket.type == filters.ticket_type)

    if filters.from_date:
        query = query.filter(SupportTicket.created_at >= filters.from_date)

    if filters.to_date:
        query = query.filter(SupportTicket.created_at <= filters.to_date)
    
    if filters.priority:
        query = query.filter(SupportTicket.priority == filters.priority)

    sort_field = getattr(SupportTicket, filters.sort_by , SupportTicket.created_at)
    if filters.sort_dir == 'desc':
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()
    
    query = query.order_by(sort_field)
    total = query.count()
    tickets = query.offset((filters.page - 1) * filters.page_size).limit(filters.page_size).all()

    return tickets, total

def update_ticket(db: Session, payload: TicketUpdate, current_user: User):
    ticket = db.query(SupportTicket).filter(SupportTicket.id == payload.ticket_id).first()

    if not ticket:
        raise Exception("Ticket not found")

    # Store old values
    old_status = ticket.status
    old_priority = ticket.priority
    old_type = ticket.type
    old_assigned = ticket.assigned_to

    action_messages = []
    updated_fields = []

    # Assignment
    if payload.user_id and payload.user_id != old_assigned:
        assignee = db.query(User).filter(User.id == payload.user_id).first()
        ticket.assigned_to = payload.user_id
        action_messages.append(
            f"Ticket assigned to {assignee.first_name} by {current_user.first_name}"
        )
        updated_fields.append("Assignee")

    # Status update
    if payload.status and payload.status != old_status:
        ticket.status = payload.status
        action_messages.append(
            f"Status changed to {payload.status.upper()} by {current_user.first_name}"
        )
        updated_fields.append("Status")

    # Type update
    if payload.ticket_type and payload.ticket_type != old_type:
        ticket.type = payload.ticket_type
        action_messages.append(
            f"Type changed to {payload.ticket_type.capitalize()} by {current_user.first_name}"
        )
        updated_fields.append("Type")

    # Priority update
    if payload.priority and payload.priority != old_priority:
        ticket.priority = payload.priority
        action_messages.append(
            f"Priority changed to {payload.priority.capitalize()} by {current_user.first_name}"
        )
        updated_fields.append("Priority")

    db.commit()
    db.refresh(ticket)

    # Detect sender role
    if ticket.user_id == current_user.id:
        sender_role = SenderRole.USER
    else:
        if current_user.role == RoleTypeEnum.SUPERADMIN or current_user.role == RoleTypeEnum.PLATFORM_ADMIN:
            sender_role = SenderRole.ADMIN
        elif current_user.role == RoleTypeEnum.DEVELOPER:
            sender_role = SenderRole.DEVELOPER
        elif current_user.role == RoleTypeEnum.SALES:
            sender_role = SenderRole.SALES
        elif current_user.role == RoleTypeEnum.SUPPORT:
            sender_role = SenderRole.SUPPORT
        else:
            sender_role = SenderRole.USER  # fallback

    # Save internal ticket messages
    for msg in action_messages:
        db.add(SupportMessage(
            ticket_id=ticket.id,
            sender_id=None,
            sender_role=sender_role,
            content=msg
        ))

    # Send notification (real-time + DB)
    if updated_fields:
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(send_notification(
                db,
                NotificationCreate(
                    user_id=ticket.user_id,
                    type="support",
                    message=f"Your support ticket #{ticket.id} has been updated ({', '.join(updated_fields)})",
                    url="/support"
                )
            ))
        except RuntimeError:
            asyncio.run(send_notification(
                db,
                NotificationCreate(
                    user_id=ticket.user_id,
                    type="support",
                    message=f"Your support ticket #{ticket.id} has been updated ({', '.join(updated_fields)})",
                    url="/support"
                )
            ))

    db.commit()
    return ticket
