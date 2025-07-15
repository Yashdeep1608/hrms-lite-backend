import enum

class BusinessTypeEnum(str, enum.Enum):
    PRODUCT_BASED = "product_based"
    SERVICE_BASED = "service_based"
    BOTH = "hybrid"
    DIGITAL = "digital"

class RoleTypeEnum(int,enum.Enum):
    SuperAdmin = 1
    Admin = 2
    Employee = 3

class OtpTypeEnum(str,enum.Enum):
    Register = "register"
    Login = "login"
    ForgetPassword = "forget_password"
    ResetPassword = "reset_Password"
    UpdatePhone = "update_phone"

class PermissionTypeEnum(str,enum.Enum):
    Page = "page"
    Method = "method"