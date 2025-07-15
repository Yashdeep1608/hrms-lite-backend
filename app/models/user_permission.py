from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.enums import PermissionTypeEnum


class UserPermission(Base):
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    permission_id = Column(Integer, ForeignKey("permissions.id"))
    created_at = Column(DateTime(timezone = True),default=lambda: datetime.now(timezone.utc))

    users = relationship("User", back_populates="user_permissions")
    permissions = relationship("Permission", back_populates="user_permissions")
