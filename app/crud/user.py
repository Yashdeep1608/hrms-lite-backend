from datetime import timedelta, datetime, timezone
import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_otp import UserOTP
from app.schemas.user import ChangePassword, UserUpdate, VerifyOtp
from app.core.security import *
from app.models.enums import RoleTypeEnum
from app.core.config import settings
from sqlalchemy.orm import joinedload

def get_user_by_email_or_phone(db:Session,data:str):
    return db.query(User).filter(
                    ((User.username == data) | (User.phone_number == data)),
                    User.is_deleted == False
                )
            

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()
# Create Ne User
def create_user(
    db: Session,
    isd_code: str,
    phone_number: str,
    role: RoleTypeEnum,
    first_name: str = None,
    last_name: str = None,
    email: str = None,
):
    """
    Create a basic user after OTP verification.
    Role can be SUPERADMIN, ADMIN, or EMPLOYEE.
    """

    # Generate temporary username
    temp_username = "user_" + "".join(
        random.choices(string.ascii_lowercase + string.digits, k=6)
    )

    # Generate temporary password (hashed)
    temp_password = get_password_hash("Temp@1234")

    new_user = User(
        first_name=first_name or f"User-{phone_number}",
        last_name=last_name or "",
        email=email,
        isd_code=isd_code,
        phone_number=phone_number,
        username=temp_username,
        password=temp_password,
        role=role.value,  # Store enum value
        is_phone_verified=True,
        is_email_verified=False,
        is_active=True,
        is_deleted=False,
        profile_image=None,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user


def create_otp_for_user(
    db: Session,
    otp_type: str,
    user: Optional[User] = None,
    isd_code: Optional[str] = None,
    phone_number: Optional[str] = None
):
    """
    Create OTP for existing user OR for pre-registration (phone-based signup)
    """
    # OTP generation
    while True:
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        if otp_code != settings.ADMIN_BYPASS_OTP:
            break

    if user:
        user_otp = UserOTP(
            user_id=user.id,
            otp=otp_code,
            type=otp_type,
            is_sent=False,
            is_verified=False
        )
    else:
        if not isd_code or not phone_number:
            raise ValueError("isd_code and phone_number are required for OTP without user")
        user_otp = UserOTP(
            user_id=None,
            isd_code=isd_code,
            phone_number=phone_number,
            otp=otp_code,
            type=otp_type,
            is_sent=False,
            is_verified=False
        )

    db.add(user_otp)
    db.commit()
    db.refresh(user_otp)

    return user_otp
# Mark OTP as Sent
def mark_otp_as_sent(db: Session, user_otp: UserOTP):
    user_otp.is_sent = True
    db.commit()
    db.refresh(user_otp)
    return user_otp
#Verify OTP
def verify_otp(db: Session, payload: VerifyOtp):
    otp_code = payload.otp
    otp_type = payload.otp_type
    user_id = payload.user_id
    isd_code = payload.isd_code
    phone_number = payload.phone_number

    filters = [
        UserOTP.type == otp_type,
        UserOTP.is_verified == False
    ]

    # If user_id provided, match by user_id
    if user_id:
        filters.append(UserOTP.user_id == user_id)
    else:
        filters.append(UserOTP.isd_code == isd_code)
        filters.append(UserOTP.phone_number == phone_number)

    # Only add OTP match filter if not the admin bypass OTP
    if otp_code != settings.ADMIN_BYPASS_OTP:
        filters.append(UserOTP.otp == otp_code)

    # Get latest OTP
    otp_entry = (
        db.query(UserOTP)
        .filter(*filters)
        .order_by(UserOTP.created_at.desc())
        .first()
    )

    if not otp_entry:
        raise Exception("invalid_or_used_otp")

    # Ensure timezone awareness for expiry check
    created_at = otp_entry.created_at
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)

    if datetime.now(timezone.utc) > created_at + timedelta(minutes=10):
        raise Exception("otp_expired")

    # Mark OTP as verified
    otp_entry.is_verified = True
    db.commit()
    return otp_entry
# Reset User Password
def reset_user_password(db: Session, user_id:int ,new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    user.password = get_password_hash(new_password)
    db.commit()
    return user
# Soft Delete User
def soft_delete_user(db: Session, user: User):
    user.is_active = False
    user.is_deleted = True
    db.commit()
# Update User
def update_user(db: Session, user_id: int, data: UserUpdate):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception("user_not_found")

        data_dict = data.model_dump(exclude_unset=True)

        # Update all fields except referral_code
        for field, value in data_dict.items():
            if hasattr(user, field):
                setattr(user, field, value)

        if data.password:
            user.password = get_password_hash(data.password)
        

        user.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(user)
        return user

    except Exception as e:
        db.rollback()
        raise
# Change User Password
def changePassword(db: Session, payload:ChangePassword):
    try:
        user = db.query(User).filter(User.id == payload.user_id).first()
        if not user:
            raise Exception("user_not_found")
        if not verify_username_password(payload.current_password, user.password):
            raise Exception("current_password_mismatch")
        user.password = get_password_hash(payload.new_password)
        db.commit()
        return user
    except Exception as e:
        db.rollback()
        raise e   
