from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import BannerLinkType, BannerPosition

class Banner(Base):
    __tablename__ = "banners"

    id = Column(Integer, primary_key=True, autoincrement=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=True)  # Null = platform banner

    title = Column(String(100), nullable=True)  # Can support multilingual
    image_url = Column(String(1000), nullable=False)

    link_type = Column(Enum(BannerLinkType), nullable=True)
    link_target_id = Column(Integer, nullable=True)  # ID of the target product/service/etc
    external_url = Column(String, nullable=True)

    position = Column(Enum(BannerPosition), nullable=True)  # Where to show this
    display_order = Column(Integer, default=0)

    start_datetime = Column(DateTime(timezone=True), nullable=True)
    end_datetime = Column(DateTime(timezone=True), nullable=True)

    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)

    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="banners")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_banners")