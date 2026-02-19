from pydantic import BaseModel, EmailStr, Field
from typing import Optional,List



class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    isd_code: str
    phone_number: str
    username: str
    password: str
    profile_image:Optional[str] = None

class UserUpdate(BaseModel):
    first_name:Optional[str] = None
    last_name:Optional[str] = None
    email:Optional[EmailStr] = None
    isd_code:Optional[str] = None
    password:Optional[str] = None
    phone_number:Optional[str] = None
    profile_image:Optional[str] = None
    is_active:Optional[bool] = True

class UserLogin(BaseModel):
    username: str
    password: str

class ForgetPassword(BaseModel):
    email_or_phone: str

class ResetPassword(BaseModel):
    user_id: int
    new_password: str

class VerifyOtp(BaseModel):
    otp_type: str
    otp: str
    user_id: Optional[int] = None
    isd_code: Optional[str] = None
    phone_number: Optional[str] = None
class SendOtp(BaseModel):
    user_id: Optional[int] = None
    otp_type: Optional[str] = None
    isd_code: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None

class ChangePassword(BaseModel):
    user_id: int
    current_password: str
    new_password: str
