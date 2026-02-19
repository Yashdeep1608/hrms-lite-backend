from pydantic import BaseModel, EmailStr
from datetime import date
from enum import Enum


class AttendanceStatus(str, Enum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"


class EmployeeCreate(BaseModel):
    full_name: str
    email: EmailStr
    department: str


class EmployeeResponse(BaseModel):
    id: int
    employee_code: str
    full_name: str
    email: str
    department: str

    class Config:
        from_attributes = True


class AttendanceCreate(BaseModel):
    employee_id: int
    date: date
    status: AttendanceStatus


class AttendanceResponse(BaseModel):
    id: int
    employee_id: int
    date: date
    status: AttendanceStatus

    class Config:
        from_attributes = True
