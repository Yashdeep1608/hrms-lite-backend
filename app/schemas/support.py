from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.enums import TicketType, TicketPriority, TicketStatus, SupportRole, SenderRole, TicketActionType

# ------- GUEST Ticket -------
class GuestTicketCreate(BaseModel):
    guest_name: str = Field(..., max_length=100)
    guest_email: EmailStr
    type: TicketType
    subject: str
    content: str

# ------- Logged-in Ticket -------
class TicketCreate(BaseModel):
    type: TicketType
    subject: str
    content: str
    is_premium:bool
    attachments: Optional[List[str]] = []  # URLs or upload keys

# ------- Ticket Message -------
class TicketMessageCreate(BaseModel):
    message: str
    attachment_urls: Optional[List[str]] = None  # For image/docs support
    status: Optional[str] = None  # e.g., "closed"

# ------- Assignment -------
class TicketAssignment(BaseModel):
    assigned_to: int
    assigned_role: SupportRole

# ------- Status / Priority Change -------
class TicketStatusChange(BaseModel):
    status: TicketStatus

class TicketPriorityChange(BaseModel):
    priority: TicketPriority

# ------- Response Schemas -------
class TicketBaseOut(BaseModel):
    id: int
    subject: str
    type: TicketType
    status: TicketStatus
    priority: TicketPriority
    is_premium: bool
    created_at: datetime

class TicketMessageOut(BaseModel):
    id: int
    content: str
    sender_role: Optional[SenderRole]
    sent_at: datetime
    attachments: List[str]

class TicketThreadOut(TicketBaseOut):
    messages: List[TicketMessageOut]

class TicketActionLogOut(BaseModel):
    action_type: TicketActionType
    actor_id: Optional[int]
    old_value: Optional[str]
    new_value: Optional[str]
    notes: Optional[str]
    created_at: datetime

class TicketFilters(BaseModel):
    search: Optional[str] = None
    status: Optional[str] = None
    ticket_type: Optional[str] = None
    priority:Optional[str] = None
    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None
    assigned_to_user_id: Optional[int] = None  # If needed for filtering
    sort_by:Optional[str] = 'created_at'
    sort_dir:Optional[str] = 'desc'
    page: int = 1
    page_size: int = 10

class TicketUpdate(BaseModel):
    ticket_id:int
    ticket_type:Optional[str]
    status:Optional[str]
    priority:Optional[str]
    user_id:Optional[int]