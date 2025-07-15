from datetime import timedelta, datetime, timezone
import random
import string
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.user_otp import UserOTP
from app.schemas.user import ChangePassword,UserCreate, UserOut, UserUpdate
from app.core.security import *
from app.models.enums import RoleTypeEnum
from app.models.permission import Permission  # Adjust import if needed
from app.models.user_permission import UserPermission  # Adjust import if needed
from app.models.business import Business  # Adjust import if needed
from app.schemas.business import BusinessOut
from app.core.config import settings


def generate_unique_referral_code(db: Session, length: int = 8) -> str:
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        existing_user = db.query(User).filter(User.referral_code == code).first()
        if not existing_user:
            return code

# Get User by user_name
def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(
        User.username == username,
        User.is_deleted == False,
        User.is_active == True
    ).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
        User.is_active == True
    ).first()

# Create Ne User
def create_user(db: Session, user_in: UserCreate):
    hashed_password = get_username_password_hash(user_in.password)
    hashed_username = get_username_password_hash(user_in.username)
    referral_code = generate_unique_referral_code(db)
    
    db_user = User(
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        email=user_in.email,
        isd_code=user_in.isd_code,
        phone_number=user_in.phone_number,
        whatsapp_number=user_in.whatsapp_number,
        username=hashed_username,
        password=hashed_password,
        referral_code=referral_code,
        role=RoleTypeEnum.Admin,
        business_id=user_in.business_id,
        profile_image = user_in.profile_image,
        parent_user_id = user_in.parent_user_id or None,
        referred_by = user_in.referred_by or None,

    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

# Get User by email/phone
def get_user_by_email_or_phone(db: Session, email_or_phone: str):
    return db.query(User).filter(
        (User.username == email_or_phone) | (User.phone_number == email_or_phone),User.is_deleted == False, User.is_active == True
    ).first()

# Create OTP for User
def create_otp_for_user(otp_type: str,db: Session, user: User):
    while True:
        otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        if otp_code != settings.ADMIN_BYPASS_OTP:
            break

    user_otp = UserOTP(
        user_id=user.id,
        otp=otp_code,
        type= otp_type,
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

def verify_otp(db: Session, user_id: int, otp_code: str, otp_type: str):
    filters = [
        UserOTP.user_id == user_id,
        UserOTP.type == otp_type,
        UserOTP.is_verified == False
    ]

    # Only add OTP match filter if not the admin bypass OTP
    if otp_code != settings.ADMIN_BYPASS_OTP:
        filters.append(UserOTP.otp == otp_code)

    otp_entry = db.query(UserOTP).filter(*filters).order_by(UserOTP.created_at.desc()).first()

    if not otp_entry:
        return None, "invalid_or_used_otp"

    # Ensure timezone awareness
    created_at = otp_entry.created_at.replace(tzinfo=timezone.utc) if otp_entry.created_at.tzinfo is None else otp_entry.created_at

    if datetime.now(timezone.utc) > created_at + timedelta(minutes=10):
        return None, "otp_expired"

    otp_entry.is_verified = True
    db.commit()
    db.refresh(otp_entry)
    return otp_entry, None


# Reset User Password
def reset_user_password(db: Session, user_id:int ,new_password: str):
    user = db.query(User).filter(User.id == user_id).first()
    user.password = get_username_password_hash(new_password)
    db.commit()
    return user

# Soft Delete User
def soft_delete_user(db: Session, user: User):
    user.is_active = False
    user.is_deleted = True
    db.commit()

# Complete User Data
def get_user_profile_data(db: Session, user: User):
    # Validate user data using Pydantic
    user_data = UserOut.model_validate(user) if user else None

    # Fetch business
    business = db.query(Business).filter(
        Business.id == user.business_id,
        Business.is_deleted == False
    ).first()
    business_data = BusinessOut.model_validate(business) if business else None

    combined_keys = []
    if user.roles.name.lower() != "superadmin":
       # Get default permissions based on role
        role_column = f"default_{user.roles.name.lower()}"
        default_permissions = db.query(Permission).filter(
            getattr(Permission, role_column) == True
        ).all()
        default_keys = {p.key for p in default_permissions}

        # User-specific permission overrides
        user_permissions = db.query(UserPermission).filter(
            UserPermission.user_id == user.id
        ).all()
        user_keys = {perm.permissions.key for perm in user_permissions}

        combined_keys = default_keys.union(user_keys)
    

    return {
        "user": user_data.model_dump(mode="json"),
        "business": business_data.model_dump(mode="json") if business_data else None,
        "permissions": list(combined_keys)
    }

# Update User
def update_user(db: Session, user:User, data: UserUpdate):
    try:
        data_dict = data.model_dump(exclude_unset=True)

        for field, value in data_dict.items():
            if hasattr(user, field):
                setattr(user, field, value)

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
        user.password = get_username_password_hash(payload.new_password)
        db.commit()
        return user
    except Exception as e:
        db.rollback()
        raise e
    
# Get User by Referral Code
def get_user_by_referral_code(db: Session, referral_code: str):
    try:
        user = db.query(User.id).filter(User.referral_code == referral_code).first()
        if not user:
            raise Exception("referral_code_invalid")
        return user
    except Exception as e:
        raise e
    
