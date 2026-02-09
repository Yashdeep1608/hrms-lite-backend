# models/contact.py
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Index, Integer, Numeric, String, ForeignKey, Text, Boolean, TIMESTAMP, UniqueConstraint,
    DateTime, Table
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
import uuid

from app.db.base import Base

# 1. Global Contacts
class Contact(Base):
    __tablename__ = 'contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
   
    isd_code = Column(String,nullable=True)
    phone_number = Column(String, index=True)
    email = Column(String, nullable=True)
    
    country_code=Column(String,nullable=True)
    gender=Column(String,nullable=True)
    preferred_language = Column(String,default='en')

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    business_contacts = relationship("BusinessContact", back_populates="contact")


# 2. Business-Specific Contact View
class BusinessContact(Base):
    __tablename__ = 'business_contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(Integer, nullable=False, index=True)
    contact_id = Column(UUID(as_uuid=True), ForeignKey('contacts.id'), nullable=False)
    first_name = Column(String, nullable=True)
    last_name = Column(String,nullable=True)
    label = Column(String, nullable=True)  # e.g., Customer, Vendor, Patient
    notes = Column(Text, nullable=True)
    is_favorite = Column(Boolean, default=False)

    sponsor_id = Column(UUID(as_uuid=True), ForeignKey("business_contacts.id"), nullable=True)

    managed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    address_line1 = Column(String,nullable=True)
    address_line2 = Column(String,nullable=True)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    country = Column(String, nullable=True)
    postal_code = Column(String,nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    contact = relationship("Contact", back_populates="business_contacts")
    custom_values = relationship("ContactCustomValue", back_populates="business_contact", cascade="all, delete")
    carts = relationship("Cart", back_populates="business_contact", cascade="all, delete")
    orders = relationship("Order", back_populates="business_contact")
    tag_links = relationship("BusinessContactTag", back_populates="business_contact", cascade="all, delete")
    group_links = relationship("GroupContact", back_populates="business_contact", cascade="all, delete")
    ledgers = relationship("BusinessContactLedger", back_populates="business_contact", cascade="all, delete")
    sponsor = relationship("BusinessContact", remote_side=[id], backref="downlines")
    managed_by_user = relationship("User", back_populates="business_contacts_managed")


# 3. Custom Field Definitions
class ContactCustomField(Base):
    __tablename__ = 'contact_custom_fields'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # string, number, date, dropdown,boolean etc.
    is_required = Column(Boolean, default=False)
    options = Column(JSONB, nullable=True)  # For dropdowns

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    values = relationship("ContactCustomValue", back_populates="field", cascade="all, delete", passive_deletes=True)


# 4. Field Values per Business Contact
class ContactCustomValue(Base):
    __tablename__ = 'contact_custom_values'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False)
    field_id = Column(UUID(as_uuid=True), ForeignKey('contact_custom_fields.id'), nullable=False)
    value = Column(Text, nullable=True)

    business_contact = relationship("BusinessContact", back_populates="custom_values")
    field = relationship("ContactCustomField", back_populates="values", passive_deletes=True)


# 5. Tags defined per business
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(Integer, nullable=False, index=True)
    name = Column(String, nullable=False)
    color = Column(String, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    creator = relationship("User", back_populates="created_tags")
    tag_links = relationship("BusinessContactTag", back_populates="tag", cascade="all, delete")


# 6. Mapping Tags to Business Contacts
class BusinessContactTag(Base):
    __tablename__ = 'business_contact_tags'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False)
    tag_id = Column(UUID(as_uuid=True), ForeignKey('tags.id'), nullable=False)
    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # ✅ Who assigned the tag
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('business_contact_id', 'tag_id', name='_unique_contact_tag'),
    )

    business_contact = relationship("BusinessContact", back_populates="tag_links")
    tag = relationship("Tag", back_populates="tag_links")
    user = relationship("User",back_populates='assigned_tags')  # Simple reverse link to user

class Groups(Base):
    __tablename__ = 'groups'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(Integer, nullable=False, index=True)

    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)

    is_dynamic = Column(Boolean, default=False)  # ✅ flag for filtered group
    filters = Column(JSONB, nullable=True)       # ✅ only used when is_dynamic = True

    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    contact_links = relationship("GroupContact", back_populates="group", cascade="all, delete-orphan")
    creator = relationship("User", back_populates="created_groups")

class GroupContact(Base):
    __tablename__ = 'group_contacts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False)
    group_id = Column(UUID(as_uuid=True), ForeignKey('groups.id'), nullable=False)

    assigned_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        UniqueConstraint('business_contact_id', 'group_id', name='_unique_group_contact'),
    )

    business_contact = relationship("BusinessContact", back_populates="group_links")
    group = relationship("Groups", back_populates="contact_links")
    user = relationship("User",back_populates="assigned_group_contacts")  # Who added this contact to group

class BusinessContactLedger(Base):
    __tablename__ = 'business_contact_ledgers'
    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    business_contact_id = Column(UUID(as_uuid=True), ForeignKey('business_contacts.id'), nullable=False)
    entry_type = Column(String, nullable=False)  # 'credit' or 'debit'
    amount = Column(Numeric(10, 2), nullable=False)
    payment_method = Column(String, nullable=True)  # required for debit
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    business_contact = relationship("BusinessContact", back_populates="ledgers")

class Lead(Base):
    __tablename__ = "leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    business_id = Column(Integer, nullable=False, index=True)

    # Lightweight identity (pre-contact)
    phone_number = Column(String, nullable=True, index=True)
    email = Column(String, nullable=True, index=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)

    # Link to contact after conversion
    business_contact_id = Column(
        UUID(as_uuid=True),
        ForeignKey("business_contacts.id"),
        nullable=True
    )

    # Lead metadata
    source = Column(String, nullable=True, index=True)
    status = Column(
        String,
        nullable=False,
        default="new"
    )  # new, contacted, qualified, converted, lost

    assigned_to = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    # Optional intelligence (future use)
    score = Column(Integer, default=0)

    # Audit
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    business_contact = relationship("BusinessContact")
    assigned_user = relationship("User")

    __table_args__ = (
        Index("idx_leads_business_status", "business_id", "status"),
        Index("idx_leads_assigned_status", "assigned_to", "status"),
    )

