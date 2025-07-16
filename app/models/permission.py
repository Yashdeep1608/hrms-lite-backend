from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String,Boolean,DateTime
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.enums import PermissionTypeEnum


class Permission(Base):
    __tablename__ = "permissions"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, nullable=False)
    type = Column(String,nullable= False)
    default_admin = Column(Boolean, default=False)
    default_employee = Column(Boolean, default=False)
    default_sales = Column(Boolean, default=False)
    default_support = Column(Boolean, default=False)
    default_platform_admin = Column(Boolean,default=False)
    default_platform_employee = Column(Boolean,default=False)
    default_developer = Column(Boolean,default=False)
    created_at = Column(DateTime(timezone = True),default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
