import enum

class BusinessTypeEnum(str, enum.Enum):
    PRODUCT_BASED = "product_based"
    SERVICE_BASED = "service_based"
    BOTH = "hybrid"
    DIGITAL = "digital"

class RoleTypeEnum(str,enum.Enum):
    # 🌐 Platform-side roles (your internal team)
    SUPER_ADMIN = "superadmin"
    PLATFORM_ADMIN = "platform_admin"
    SALES = "sales"
    SUPPORT = "support"
    DEVELOPER = "developer"

    # 🧑‍💼 Business-side roles (your customers)
    ADMIN = "admin"
    EMPLOYEE = "employee"

class OtpTypeEnum(str,enum.Enum):
    Register = "register"
    Login = "login"
    ForgetPassword = "forget_password"
    ResetPassword = "reset_Password"
    UpdatePhone = "update_phone"

class PermissionTypeEnum(str,enum.Enum):
    Page = "page"
    Method = "method"

class PaymentStatus(str,enum.Enum):
    CREATED = "created"
    SUCCESS = "success"
    FAILED = "failed"
    REFUNDED = "refunded"
    PENDING = "pending"

class OrderStatus(str, enum.Enum):
    CREATED = "created"
    PENDING = "pending"
    COMPLETED = "completed"
    REFUNDED = "refunded"  
    FAILED = "failed"
    CANCELLED = "cancelled"

class PaymentMode(str, enum.Enum):
    ONLINE = "online"  # Razorpay or other gateways
    CASH = "cash"
    MANUAL = "manual"  # Bank transfer, etc. (optional for future)

class PlanStatus(str, enum.Enum):
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    PENDING = "pending"
class CouponType(str, enum.Enum):
    PLATFORM = "platform"
    BUSINESS = "business"
class OrderType(str, enum.Enum):
    REGISTRATION = "registration"
    EMPLOYEE_ADD = "employee_add"
    FEATURE_PURCHASE = "feature_purchase"