from datetime import timedelta, datetime, timezone
import random
import string
from typing import Optional
from sqlalchemy.orm import Session
from app.models.user import User, UserPlan
from app.models.user_otp import UserOTP
from app.schemas.user import ChangePassword, CreateDownlineUser,UserCreate, UserOut, UserUpdate, VerifyOtp
from app.core.security import *
from app.models.enums import OtpTypeEnum, PlanStatus, RoleTypeEnum
from app.models.permission import Permission  # Adjust import if needed
from app.models.user_permission import UserPermission  # Adjust import if needed
from app.models.business import Business  # Adjust import if needed
from app.schemas.business import BusinessOut
from app.core.config import settings
from sqlalchemy.orm import joinedload


def generate_unique_referral_code(db: Session, length: int = 8) -> str:
    characters = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(characters, k=length))
        existing_user = db.query(User).filter(User.referral_code == code).first()
        if not existing_user:
            return code

# Get User by user_name
def get_user_by_username(db: Session, username: str):
    return db.query(User).options(
        joinedload(User.plans),
        joinedload(User.business)
    ).filter(
        User.username == username,
        User.is_deleted == False,
    ).first()

def get_user_by_id(db: Session, user_id: int):
    return db.query(User).filter(
        User.id == user_id,
        User.is_deleted == False,
    ).first()

# Create Ne User
def create_user(db: Session, isd_code: str, phone_number: str, business_id: int):
    """
    Create a placeholder user after OTP verification with minimal info.
    """
    # Generate temporary username
    temp_username = "user_" + "".join(random.choices(string.ascii_lowercase + string.digits, k=6))

    # Dummy password (hashed)
    temp_password = get_password_hash("temp_password123")

    # Generate referral code
    referral_code = generate_unique_referral_code(db)

    new_user = User(
        first_name=f"User-{phone_number}",
        last_name="",
        email="your@email.com",
        isd_code=isd_code,
        phone_number=phone_number,
        username=temp_username,
        password=temp_password,
        referral_code=referral_code,
        role=RoleTypeEnum.ADMIN,
        business_id=business_id,
        profile_image=None,
        parent_user_id=None,
        referred_by=None,
        is_phone_verified = True,
        is_active = False,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

# Get User by email/phone
def get_user_by_email_or_phone(db: Session, email_or_phone: str):
    return (
        db.query(User)
        .options(joinedload(User.business))  # eager load the related Business
        .filter(
            ((User.username == email_or_phone) | (User.phone_number == email_or_phone)),
            User.is_deleted == False
        )
        .first()
    )

# Create OTP for User
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
    if user.role.lower() != RoleTypeEnum.SUPERADMIN:
        # Get default permissions based on role
        role_column = f"default_{user.role.lower()}"
        default_permissions = db.query(Permission).filter(
            getattr(Permission, role_column) == True
        ).all()
        default_keys = {p.key for p in default_permissions}

        # Get user-specific permission overrides from new structure
        user_permission_row = db.query(UserPermission).filter(
            UserPermission.user_id == user.id
        ).first()

        user_keys = set(user_permission_row.permission_keys) if user_permission_row and user_permission_row.permission_keys else set()

        # Merge both
        combined_keys = list(default_keys.union(user_keys))
    
    redirect = None
    plan_data = None
    reason = None

    # Check phone verification first (applies to all roles)
    if not user.is_phone_verified:
        redirect = 'verify-otp'
        reason = "phone_verification"

    # For Admins, check active user plan
    elif user.role.lower() == RoleTypeEnum.ADMIN:
        user_plan = db.query(UserPlan).filter(
            UserPlan.user_id == user.id,
            UserPlan.status == PlanStatus.ACTIVE
        ).first()

        now = datetime.now(timezone.utc)

        # ✅ If plan exists, check expiration
        if user_plan:
            if user_plan.end_date and user_plan.end_date < now:
                # Update plan status to expired
                user_plan.status = PlanStatus.EXPIRED
                db.commit()
                db.refresh(user_plan)
                redirect = 'make-payment'
                reason = "plan_expired"
            else:
                # ✅ Plan is valid and active
                plan_data = {
                    "plan_name": user_plan.plan.name if user_plan.plan else None,
                    "start_date": str(user_plan.start_date),
                    "end_date": str(user_plan.end_date),
                    "is_trial": user_plan.is_trial,
                    "status": user_plan.status,
                    "payment_id": str(user_plan.payment_id) if user_plan.payment_id else None
                }
        else:
            # ❌ No active plan
            redirect = 'make-payment'
            reason = "plan_missing"

    return {
        "user": user_data.model_dump(mode="json"),
        "business": business_data.model_dump(mode="json") if business_data else None,
        "permissions": list(combined_keys),
        "redirect":redirect,
        "reason":reason,
        "plan":plan_data
    }

# Update User
def update_user(db: Session, user_id: int, data: UserUpdate):
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise Exception("user_not_found")

        data_dict = data.model_dump(exclude_unset=True)

        # Update all fields except referral_code
        for field, value in data_dict.items():
            if field != "referral_code" and hasattr(user, field):
                setattr(user, field, value)

        # Handle referral_code separately (only for referred_by assignment)
        if data.referral_code:
            source_user = db.query(User).filter(User.referral_code == data.referral_code).first()
            if source_user:
                user.referred_by = source_user.id

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
    
# Get User by Referral Code
def get_user_by_referral_code(db: Session, referral_code: str):
    try:
        user = db.query(User.id).filter(User.referral_code == referral_code).first()
        if not user:
            raise Exception("referral_code_invalid")
        return user
    except Exception as e:
        raise e
    
# Get Platform's Users
def get_platform_user_list(db:Session,user:User):
    query = db.query(User).filter(User.role.notin_([RoleTypeEnum.ADMIN, RoleTypeEnum.EMPLOYEE]))

    if user.role == RoleTypeEnum.SUPERADMIN:
        # See all users except Admin and Employee
        users = query.all()
    elif user.role == RoleTypeEnum.PLATFORM_ADMIN:
        # Only see users created by this platform admin
        users = query.filter(User.parent_user_id == user.id).all()
    else:
        # No access to platform-level user list
        users = []

    return users

# Create Downline Users
def create_downline_user(db:Session,payload:CreateDownlineUser,user:User):
    # Generate referral code
    referral_code = generate_unique_referral_code(db)
    hashed_password = get_password_hash(payload.password)
    new_user = User(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone_number=payload.phone_number,
        whatsapp_number=payload.whatsapp_number,
        username=payload.username,
        password= hashed_password,
        role=payload.role,
        business_id=payload.business_id or user.business_id,
        preferred_language=payload.preferred_language,
        parent_user_id=user.id,
        referred_by=None,
        referral_code=referral_code,
        is_email_verified=False,
        is_phone_verified=payload.is_phone_verified,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)