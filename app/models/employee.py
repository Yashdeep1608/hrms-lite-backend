import enum

from sqlalchemy import Column, Date, Integer, String, Boolean, ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.dialects.postgresql import JSONB
import uuid
from sqlalchemy.orm import relationship
from app.db.base import Base
from datetime import datetime, timezone

class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    employee_code = Column(String(50), unique=True, nullable=False)
    full_name = Column(String(150), nullable=False)
    email = Column(String(150), unique=True, nullable=False)
    department = Column(String(100), nullable=False)

    attendance_records = relationship(
        "Attendance",
        back_populates="employee",
        cascade="all, delete-orphan"
    )

class AttendanceStatusEnum(str, enum.Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class Attendance(Base):
    __tablename__ = "attendance"

    __table_args__ = (
        UniqueConstraint("employee_id", "date", name="unique_employee_date"),
    )

    id = Column(Integer, primary_key=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"))
    date = Column(Date, nullable=False)
    status = Column(String(20), nullable=False)

    employee = relationship("Employee", back_populates="attendance_records")
