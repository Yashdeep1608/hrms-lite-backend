import random
import string
from sqlalchemy.orm import Session
from app.models.user import User
from app.core.security import *
from app.models.enums import RoleTypeEnum

def get_user_by_email_or_phone(db:Session,data:str):
    return db.query(User).filter(
                    ((User.username == data) | (User.phone_number == data)),
                    User.is_deleted == False
                ).first()
            

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
