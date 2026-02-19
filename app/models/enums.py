import enum

class RoleTypeEnum(str,enum.Enum):
    # 🌐 Platform-side roles (your internal team)
    SUPERADMIN = "superadmin"
    ADMIN = "ADMIN"
    EMPLOYEE = "employee"

class OtpTypeEnum(str,enum.Enum):
    Register = "register"
    Login = "login"
    ForgetPassword = "forget_password"
    ResetPassword = "reset_Password"
    UpdatePhone = "update_phone"

    IN_STOCK = "in_stock"
    OUT_OF_STOCK = "out_of_stock"
    LOW_STOCK = "low_stock"