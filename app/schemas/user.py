from pydantic import BaseModel, EmailStr, Field
from typing import Optional,List

from app.schemas.business import BusinessOut


class UserCreate(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    isd_code: str
    phone_number: str
    whatsapp_number: str
    username: str
    password: str
    business_id: int
    profile_image:Optional[str] = None
    parent_user_id:Optional[int] = None
    referral_code:Optional[str] = None
    referred_by:Optional[str] = None

class UserUpdate(BaseModel):
    first_name:Optional[str] = None
    last_name:Optional[str] = None
    email:Optional[EmailStr] = None
    isd_code:Optional[str] = None
    password:Optional[str] = None
    phone_number:Optional[str] = None
    profile_image:Optional[str] = None
    referral_code:Optional[str] = None
    is_active:Optional[bool] = True

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    business_id:int
    first_name: str
    last_name: str
    email: EmailStr
    username: str
    is_active: bool
    preferred_language: str
    profile_image:Optional[str] = None
    isd_code:Optional[str] = None
    phone_number:Optional[str] = None
    whatsapp_number:Optional[str] = None
    is_email_verified:bool
    is_phone_verified:bool
    username:Optional[str] = None
    password:Optional[str] = None
    role:str
    referral_code:str
    is_active:bool
    is_deleted:bool

    model_config = {
        "from_attributes": True
    }
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

class UserResponse(BaseModel):
    user:UserOut
    business:BusinessOut
    permissions:List[str]

class ChangePassword(BaseModel):
    user_id: int
    current_password: str
    new_password: str

class CreateDownlineUser(BaseModel):
    first_name: str
    last_name: str
    email: Optional[EmailStr] = None
    isd_code:Optional[str]='+91'
    phone_number: str
    password: str
    role: str
class UpdatePermission(BaseModel):
    user_id:int
    permissions:List[str]