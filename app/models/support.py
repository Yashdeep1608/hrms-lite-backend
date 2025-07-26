from sqlalchemy import Column, DateTime, ForeignKey, Integer, Boolean,String,Enum, Text
from sqlalchemy import func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import SenderRole, SupportRole, TicketActionType, TicketPriority, TicketStatus, TicketType

class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    business_id = Column(Integer,ForeignKey("businesses.id"),nullable=True)
    # Anonymous guest info for guest tickets
    guest_name = Column(String(100), nullable=True)
    guest_email = Column(String(255), nullable=True)

    type = Column(Enum(TicketType), nullable=False)
    subject = Column(String(255), nullable=False)
    status = Column(Enum(TicketStatus), default=TicketStatus.OPEN, nullable=False)
    priority = Column(Enum(TicketPriority), default=TicketPriority.NORMAL, nullable=False)
    
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_role = Column(Enum(SupportRole), nullable=True)
    is_premium = Column(Boolean, default=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    business = relationship("Business", back_populates="tickets")
    messages = relationship("SupportMessage", back_populates="ticket", cascade="all, delete-orphan")
    attachments = relationship("TicketAttachment", back_populates="ticket", cascade="all, delete-orphan")
    history = relationship("TicketActionLog", back_populates="ticket", cascade="all, delete-orphan")
    user = relationship("User", foreign_keys=[user_id], back_populates="created_tickets")
    assigned_user = relationship("User", foreign_keys=[assigned_to], back_populates="assigned_tickets")


# ---------------------
# SUPPORT MESSAGE THREAD
# ---------------------
class SupportMessage(Base):
    __tablename__ = "support_messages"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Or null for guest
    sender_role = Column(Enum(SenderRole), nullable=True)
    content = Column(Text, nullable=False)
    sent_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ticket = relationship("SupportTicket", back_populates="messages")
    attachments = relationship("MessageAttachment", back_populates="message", cascade="all, delete-orphan")
    sender = relationship("User", foreign_keys=[sender_id], back_populates="support_messages")

# ---------------------
# TICKET ATTACHMENTS
# ---------------------
class TicketAttachment(Base):
    __tablename__ = "ticket_attachments"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    uploaded_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    ticket = relationship("SupportTicket", back_populates="attachments")

# ---------------------
# MESSAGE ATTACHMENTS (Optional)
# ---------------------
class MessageAttachment(Base):
    __tablename__ = "message_attachments"

    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, ForeignKey("support_messages.id"), nullable=False)
    file_url = Column(String(500), nullable=False)
    
    message = relationship("SupportMessage", back_populates="attachments")

# ---------------------
# TICKET ACTION / AUDIT LOG
# ---------------------
class TicketActionLog(Base):
    __tablename__ = "ticket_action_logs"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("support_tickets.id"), nullable=False)
    actor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action_type = Column(Enum(TicketActionType), nullable=False)
    old_value = Column(String(100))
    new_value = Column(String(100))
    notes = Column(Text)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    ticket = relationship("SupportTicket", back_populates="history")
    actor = relationship("User", foreign_keys=[actor_id], back_populates="ticket_logs")
