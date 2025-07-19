import enum

class BusinessTypeEnum(str, enum.Enum):
    PRODUCT_BASED = "product_based"
    SERVICE_BASED = "service_based"
    BOTH = "hybrid"
    DIGITAL = "digital"

class RoleTypeEnum(str,enum.Enum):
    # 🌐 Platform-side roles (your internal team)
    SUPERADMIN = "superadmin"
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

class CreditType(str,enum.Enum):
    REFERRAL_USER = 'referral_user'              # When a business user refers another user
    REFERRAL_EMPLOYEE = 'referral_employee'      # When an employee refers a user
    COUPON_REFERRAL = 'coupon_referral'          # When a referral comes via coupon
    PLATFORM_BONUS = 'platform_bonus'            # Platform-side reward (sales/dev/support)
    MANUAL_ADJUSTMENT = 'manual_adjustment'      # Admin manually credits/debits
    PURCHASE_REWARD = 'purchase_reward'          # Cashback or reward on purchase

# ----------------------------
# ✅ TICKET STATUS
# ----------------------------
class TicketStatus(str, enum.Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"
    REOPENED = "reopened"
    WAITING = "waiting"
    DUPLICATE = "duplicate"

# ----------------------------
# ✅ PRIORITY LEVELS
# ----------------------------
class TicketPriority(str, enum.Enum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"
    CRITICAL = "critical"

# ----------------------------
# ✅ TYPE OF TICKET (DEPARTMENT)
# ----------------------------
class TicketType(str, enum.Enum):
    SALES = "sales"
    TECHNICAL = "technical"
    BILLING = "billing"
    OTHER = "other"
    ORDER = "order"
    FEEDBACK = "feedback"

# ----------------------------
# ✅ ASSIGNED SUPPORT ROLE
# ----------------------------
class SupportRole(str, enum.Enum):
    SUPPORT = "support"
    SALES = "sales"
    DEVELOPER = "developer"

class SenderRole(str, enum.Enum):
    GUEST = "guest"
    USER = "user"
    SUPPORT = "support"
    ADMIN = "admin"
    DEVELOPER = "developer"
    SALES = "sales"
class TicketActionType(str, enum.Enum):
    STATUS_CHANGE = "status_change"
    PRIORITY_CHANGE = "priority_change"
    ASSIGNMENT = "assignment"
    COMMENT = "comment"
    INTERNAL_NOTE = "internal_note"
    REOPEN = "reopen"
    CLOSE = "close"
    ATTACHMENT_ADDED = "attachment_added"