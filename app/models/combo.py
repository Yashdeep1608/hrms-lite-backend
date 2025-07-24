from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Float, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import ComboType
from sqlalchemy.dialects.postgresql import JSONB

class Combo(Base):
    __tablename__ = "combos"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)  # Null = platform combo

    name = Column(JSONB, nullable=False)
    slug = Column(String, unique=True, nullable=False)
    description = Column(JSONB, nullable=True)

    combo_price = Column(Float, nullable=False)
    discount_type = Column(String, default="none")
    discount_value = Column(Float, nullable=True)
    max_discount = Column(Float, nullable=True)

    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=False)
    is_featured = Column(Boolean, default=False)
    image_url = Column(String, nullable=True)

    created_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    business = relationship("Business", back_populates="combos")
    items = relationship("ComboItem", back_populates="combo", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_combo")

class ComboItem(Base):
    __tablename__ = "combo_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    combo_id = Column(Integer, ForeignKey("combos.id"), nullable=False)

    item_type = Column(Enum(ComboType), nullable=False)
    item_id = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False, default=1)

    combo = relationship("Combo", back_populates="items")