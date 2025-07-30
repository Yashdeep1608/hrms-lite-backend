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

class ComboType(str,enum.Enum):
    PRODUCT = "product"
    SERVICE = "service"

class OfferConditionType(str, enum.Enum):
    PRODUCT = "product"                 # product_id(s)
    SERVICE = "service"                 # service_id(s)
    CATEGORY = "category"               # category_id(s)
    CART_TOTAL = "cart_total"           # minimum cart value
    CONTACT_TAG = "contact_tag"         # contact has tag X
    FIRST_ORDER = "first_order"         # only if user has no prior orders
    CONTACT_GROUP = "contact_group"     # contact in group
    TIME_WINDOW = "time_window"         # applied only within a time window
    PAYMENT_METHOD = "payment_method"   # COD, Online, Wallet etc.

class OfferRewardType(str, enum.Enum):
    FLAT = "flat"                            # ₹50 off
    PERCENTAGE = "percentage"                # 10% off
    FREE_PRODUCT = "free_product"            # get 1 product free
    DISCOUNTED_PRODUCT = "discounted_product" # product at ₹X
    FREE_SERVICE = "free_service"            # get 1 service free
    DISCOUNTED_SERVICE = "discounted_service" # service at ₹X
    CASHBACK = "cashback"                    # cashback credited
    FREE_SHIPPING = "free_shipping"          # waive delivery fees

class ConditionOperator(str, enum.Enum):
    EQUALS = "equals"
    IN = "in"
    NOT_IN = "not_in"
    GTE = "gte"
    LTE = "lte"
    BETWEEN = "between"

class OfferType(str, enum.Enum):
    FLAT_DISCOUNT = "flat_discount"             # ₹50 off
    PERCENTAGE_DISCOUNT = "percentage_discount" # 10% off
    BUY_X_GET_Y = "buy_x_get_y"                 # Buy 2 get 1 free
    BUNDLE_PRICING = "bundle_pricing"           # Buy combo of A+B for ₹300
    CART_VALUE_BASED = "cart_value_based"       # ₹100 off on cart >= ₹999
    CUSTOMER_BASED = "customer_based"           # For first-time or specific users
    TIME_LIMITED = "time_limited"               # Flash Sale / Happy Hours

class BannerPosition(str,enum.Enum):
    HOMEPAGE = "homepage"
    CATEGORY_PAGE = "category_page"
    SERVICE_PAGE = "service_page"
    OFFER_ZONE = "offer_zone"
    POPUP = "popup"
    TOP_BAR = "top_bar"

class BannerLinkType(str,enum.Enum):
    PRODUCT = "product"
    SERVICE = "service"
    CATEGORY = "category"
    COMBO = "combo"
    OFFER = "offer"
    EXTERNAL = "external"

class ScheduleType(str, enum.Enum):
    TIME_SLOT = "time_slot"
    FIXED = "fixed"
    DURATION = "duration"
    SUBSCRIPTION = "subscription"
    FLEXIBLE = "flexible"

class LocationType(str, enum.Enum):
    ONSITE = "onsite"
    ONLINE = "online"
    CUSTOMER_LOCATION = "customer_location"

class CartOrderSource(str, enum.Enum):
    WEB = "web"
    BACK_OFFICE = "back_office"

class CartOrderStatus(str,enum.Enum):
    PENDING = "pending"
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class OrderPaymentMode(str,enum.Enum):
    OFFLINE = "offline"
    ONLINE = "online"

class OrderPaymentMethod(str,enum.Enum):
    UPI = "upi"
    CARD = "card"
    NETBANKING = "netbanking"
    WALLET = "wallet"
    CASH = "cash"
class OrderPaymentStatus(enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"