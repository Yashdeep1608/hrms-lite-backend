import uuid
from sqlalchemy import JSON, UUID, Column, DateTime, ForeignKey, Integer, Boolean, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class ImportJob(Base):
    __tablename__ = "import_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    business_id = Column(Integer, nullable=False)
    entity_type = Column(String, nullable=False)
    # lead, contact, product, order

    file_path = Column(String, nullable=False)

    # Import behavior
    import_type = Column(
        String,
        nullable=False,
        default="create"
    )
    # create | update | upsert

    unique_field = Column(
        String,
        nullable=True
    )
    # lead: phone_number | email
    # product: sku | barcode | name
    # contact: phone | email

    # Optional post-import intent (CRM-only usage)
    assign_group_ids = Column(JSON, nullable=True)
    assign_tag_ids = Column(JSON, nullable=True)
    # Applied only when entity supports it (contacts later)
    
    status = Column(String, default="pending")
    # pending, processing, completed, failed

    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    success_rows = Column(Integer, default=0)
    failed_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    duplicate_rows = Column(Integer, default=0)
    invalid_rows = Column(Integer, default=0)
    meta = Column(JSON, nullable=True)  # For any additional info like error details

    error_file_path = Column(String, nullable=True)

    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
