#Create Order
import asyncio
from datetime import datetime, timedelta, timezone
import json
import razorpay
from requests import Session

from app.models.business import Business
from app.models.coupon import Coupon
from app.models.enums import CreditType, OrderStatus, OrderType, PaymentMode, PaymentStatus, PlanStatus, RoleTypeEnum
from app.models.notification import NotificationType
from app.models.plan import Plan
from app.models.user import User, UserCredit, UserOrder, UserPayment, UserPlan
from app.schemas.notification import NotificationCreate
from app.schemas.payment import CreateOrder, PlaceOrder, RazorpayPaymentVerify
from app.services.notifications.notification_service import send_notification
from app.services.payments.razorpay_service import create_razorpay_order, fetch_razorpay_payment
from app.services.messaging import gupshup as gupshup

def create_order(db: Session, order: CreateOrder, current_user: User):
    try:
        plan = None
        offer_discount = 0.0
        coupon_discount = 0.0
        total_price = 0.0
        subtotal = 0.0

        # ------------------------------
        # 📌 CASE 1: Plan Registration
        # ------------------------------
        if order.order_type == OrderType.REGISTRATION:
            if not order.plan_id:
                raise Exception("plan_required")

            plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
            if not plan:
                raise Exception("plan_not_found")

            offer_discount = plan.offer_discount or 0.0
            total_price = plan.price
            subtotal = total_price - offer_discount

            # Coupon logic
            if order.coupon_code:
                coupon = db.query(Coupon).filter(Coupon.code == order.coupon_code).first()
                if not coupon or not coupon.is_active:
                    raise Exception("invalid_coupon")

                now = datetime.now(timezone.utc)
                if coupon.valid_to and now > coupon.valid_to:
                    raise Exception("coupon_expired")

                if coupon.discount_type == "flat":
                    coupon_discount = coupon.discount_value
                elif coupon.discount_type == "percentage":
                    coupon_discount = round((subtotal * coupon.discount_value) / 100, 2)

                # prevent negative subtotal
                coupon_discount = min(coupon_discount, subtotal)
                subtotal -= coupon_discount

        # ------------------------------
        # 📌 CASE 2: Add Extra Users
        # ------------------------------
        elif order.order_type == OrderType.EMPLOYEE_ADD:
            if not order.extra_users or not order.per_user_price:
                raise Exception("extra_users_and_price_required")

            # base calculation: pro-rata or full cycle
            

            subtotal = order.per_user_price * order.extra_users

            # coupons are NOT applied for OrderType.EMPLOYEE_ADD
            coupon_discount = 0.0
            offer_discount = 0.0

        # ------------------------------
        # 📌 CASE 3: Feature Purchase (future use)
        # ------------------------------
        elif order.order_type == "upgrade":
            user_plan = db.query(UserPlan).filter(UserPlan.user_id == current_user.id,UserPlan.status == PlanStatus.ACTIVE).first()
            # fetch pro plan
            pro_plan = db.query(Plan).filter(Plan.name == "Pro").first()
           
            # base price of pro plan
            total_price = pro_plan.price
            offer_discount = pro_plan.offer_discount or 0.0
            subtotal = total_price - offer_discount
            coupon_discount = 0  # not applicable in upgrade
            final_amount = subtotal  # since no gst for now

            # pro rata days logic
            remaining_days = 0
            if user_plan.end_date:
                now = datetime.now(timezone.utc)
                if user_plan.end_date > now:
                    remaining_days = (user_plan.end_date - now).days
            # means: add these extra days to pro plan subscription
            order.pro_rata_days = pro_plan.duration_days + remaining_days

        else:
            raise Exception("invalid_order_type")

        # gst_percent = 18.0
        # gst_amount = round(subtotal * gst_percent / 100, 2)
        final_amount = subtotal

        return {
            "user_id": current_user.id,
            "business_id": current_user.business_id,
            "plan_id": order.plan_id if order.order_type == OrderType.REGISTRATION else None,
            "total": total_price,
            "offer_discount": offer_discount,
            "coupon_discount": coupon_discount,
            "gst_percent": 0,
            "gst_amount": 0,
            "subtotal": subtotal,
            "final_amount": final_amount,
            "extra_users": order.extra_users if order.order_type == OrderType.EMPLOYEE_ADD else None,
            "per_user_price": order.per_user_price if order.order_type == OrderType.EMPLOYEE_ADD else None,
            "pro_rata_days": order.pro_rata_days,
            "order_type": order.order_type,
        }

    except Exception as e:
        raise e
   
def place_order(db: Session, payload: PlaceOrder, current_user: User):
    try:
        # Create order record
        user_order = UserOrder(
            user_id=current_user.id,
            business_id=current_user.business_id,
            plan_id=payload.plan_id or None,
            coupon_code=payload.coupon_code or None,
            order_type=payload.order_type,
            original_amount=payload.original_amount,
            offer_discount=payload.offer_discount,
            coupon_discount=payload.coupon_discount,
            subtotal=payload.subtotal,
            gst_percent=0,
            gst_amount=payload.gst_amount,
            final_amount=payload.final_amount,
            notes=payload.notes,
            status=OrderStatus.CREATED,
            # 👇 new team member fields
            extra_users=payload.extra_users or 0,
            per_user_price=payload.per_user_price or 0.0,
            pro_rata_days=payload.pro_rata_days or 0,
        )

        db.add(user_order)
        db.commit()
        db.refresh(user_order)

        # ✅ Trial plan shortcut
        if payload.plan_id == 1:
            now = datetime.now(timezone.utc)
            start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = (start_date + timedelta(days=30)).replace(
                hour=23, minute=59, second=59, microsecond=999999
            )

            new_user_plan = UserPlan(
                user_id=user_order.user_id,
                plan_id=user_order.plan_id,
                payment_id=None,
                start_date=start_date,
                end_date=end_date,
                status=PlanStatus.ACTIVE,
                is_trial=True
            )
            # Send WhatsApp message
            valid_date = end_date.strftime("%-d %B %Y")  # Linux/Mac
            gupshup.send_whatsapp_transaction_gupshup(
                isd_code=current_user.isd_code,
                phone_number=current_user.phone_number,
                name=current_user.first_name,
                amount="₹0.00",
                valid=valid_date,
                plan="FREE Trial"
            )
            db.add(new_user_plan)
            db.commit()
            return user_order

        # ✅ Paid plan → Razorpay order
        receipt_id = str(user_order.id)
        razorpay_order = create_razorpay_order(
            amount=user_order.final_amount,
            currency="INR",
            receipt=receipt_id,
            notes={
                "user_id": str(current_user.id),
                "order_type": payload.order_type or "general",
                "extra_users": str(payload.extra_users or 0),
            },
        )

        user_order.razorpay_order_id = razorpay_order["id"]

        notes = {
            "user_id": str(current_user.id),
            "order_type": payload.order_type or "general",
            "extra_users": str(payload.extra_users or 0),
        }
        notes_str = json.dumps(notes)

        user_payment = UserPayment(
            user_id=current_user.id,
            amount=user_order.final_amount,
            currency="INR",
            receipt=str(user_order.id),
            razorpay_order_id=razorpay_order["id"],
            status=PaymentStatus.CREATED,
            is_verified=False,
            payment_mode=PaymentMode.ONLINE,
            notes=notes_str
        )
        db.add(user_payment)
        db.commit()
        db.refresh(user_order)

        return user_order

    except Exception as e:
        db.rollback()
        raise e
  
def verify_user_payment(db: Session, payload: RazorpayPaymentVerify, current_user: User):
    # Fetch payment by order_id
    payment = db.query(UserPayment).filter(
        UserPayment.razorpay_order_id == payload.order_id
    ).first()
    if not payment:
        raise Exception("payment_not_found")

    # Fetch payment details from Razorpay
    payment_data = fetch_razorpay_payment(payload.payment_id)
    payment_status = payment_data.get("status", "failed")  # captured, failed, refunded, authorized, etc.
    payment_method = payment_data.get("method", "unknown")

    # Map Razorpay status → internal PaymentStatus
    status_map = {
        "captured": PaymentStatus.SUCCESS,
        "failed": PaymentStatus.FAILED,
        "refunded": PaymentStatus.REFUNDED,
        "authorized": PaymentStatus.PENDING,
    }
    payment.status = status_map.get(payment_status, PaymentStatus.FAILED)

    # Update payment details
    payment.razorpay_payment_id = payload.payment_id
    payment.payment_method = payment_method
    payment.is_verified = True

    # Update order status
    order = db.query(UserOrder).filter(UserOrder.razorpay_order_id == payload.order_id).first()
    if order:
        # Sync order status with payment
        order_status_map = {
            PaymentStatus.SUCCESS: OrderStatus.COMPLETED,
            PaymentStatus.FAILED: OrderStatus.FAILED,
            PaymentStatus.REFUNDED: OrderStatus.REFUNDED,
            PaymentStatus.PENDING: OrderStatus.PENDING,
        }
        order.status = order_status_map.get(payment.status, OrderStatus.FAILED)

        # Handle post-payment actions
        if payment.status == PaymentStatus.SUCCESS:
            order_type_actions = {
                OrderType.REGISTRATION: lambda: register_user(db, order, current_user, payment),
                OrderType.EMPLOYEE_ADD: lambda: add_employee(db, order, current_user),
                OrderType.UPGRADE: lambda: update_user_plan(db, order, current_user, payment),
                OrderType.RENEWAL: lambda: update_user_plan(db, order, current_user, payment),
            }
            action = order_type_actions.get(order.order_type)
            if action:
                action()

    db.commit()
    return payment

def register_user(db:Session,order:UserOrder,current_user:User,payment:UserPayment):
    plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
    if not plan:
        raise Exception("plan_not_found")

    now = datetime.now(timezone.utc)
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    extra_days = 0
    if plan.id != 1:  # not trial
        extra_days = 45  # 30 (trial equivalent) + 15 (bonus for direct trust)

    end_date = (
        start_date + timedelta(days=(plan.duration_days + extra_days) or 30)
    ).replace(hour=23, minute=59, second=59, microsecond=999999)
    # Create new plan
    new_user_plan = UserPlan(
        user_id=order.user_id,
        plan_id=order.plan_id,
        payment_id=payment.id,
        start_date=start_date,
        end_date=end_date,
        status=PlanStatus.ACTIVE,
        is_trial=(plan.id == 1)
    )
    db.add(new_user_plan)
    db.commit()
    db.refresh(new_user_plan)

    # Send WhatsApp message
    valid_date = end_date.strftime("%-d %B %Y")  # Linux/Mac
    amount_str = f"₹{order.final_amount:,.2f}"
    gupshup.send_whatsapp_transaction_gupshup(
        isd_code=current_user.isd_code,
        phone_number=current_user.phone_number,
        name=current_user.first_name,
        amount=amount_str,
        valid=valid_date,
        plan="PRO"
    )

    # Referral credit only for first paid plan
    if current_user.referred_by and plan.id != 1:
        # Check if user had any previous paid plans
        paid_plan_exists = db.query(UserPlan).filter(
            UserPlan.user_id == current_user.id,
            UserPlan.plan_id != 1
        ).first()
        if not paid_plan_exists:
            add_credit(
                db=db,
                user_id=current_user.referred_by,
                source_user_id=current_user.id,
                credit_type=CreditType.REFERRAL_USER,
                meta={"reason": "User subscribed to plan", "plan_id": order.plan_id}
            )
    db.flush()

def add_employee(db:Session,order:UserOrder,current_user:User):
    business  = db.query(Business).filter(Business.id  == current_user.business_id).first()
    user = db.query(User).filter(User.id == current_user.id).first()
    if not business:
        return Exception("business_not_found")
    amount_str = f"{order.per_user_price:,.2f}"
    total_amount_str = f"{order.final_amount:,.2f}"
    gupshup.send_whatsapp_transaction2_gupshup(
        isd_code=user.isd_code,
        phone_number=user.phone_number,
        name=user.first_name,
        users=str(order.extra_users),
        amount=amount_str,
        valid=str(order.pro_rata_days),
        total_amount=total_amount_str
    )
    business.extra_users = business.extra_users + order.extra_users if business.extra_users else  order.extra_users
    db.flush()

def update_user_plan(db: Session, order: UserOrder, current_user: User, payment: UserPayment):
    now = datetime.now(timezone.utc)

    # Fetch last active plan
    active_plan = db.query(UserPlan).filter(
        UserPlan.user_id == current_user.id,
        UserPlan.status == PlanStatus.ACTIVE
    ).order_by(UserPlan.end_date.desc()).first()

    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Duration = only pro_rata_days (no base plan duration needed, since always PRO)
    total_days = order.pro_rata_days or 30  # default 30 if not passed

    end_date = (
        start_date + timedelta(days=total_days)
    ).replace(hour=23, minute=59, second=59, microsecond=999999)

    # Deactivate old plan if exists
    if active_plan:
        active_plan.status = PlanStatus.EXPIRED
        db.add(active_plan)

    # Create new plan record (always PRO)
    new_user_plan = UserPlan(
        user_id=current_user.id,
        plan_id=2,  # Hardcode PRO plan id
        payment_id=payment.id,
        start_date=start_date,
        end_date=end_date,
        status=PlanStatus.ACTIVE,
        is_trial=False
    )
    db.add(new_user_plan)
    db.commit()
    db.refresh(new_user_plan)

    # Send WhatsApp message
    valid_date = end_date.strftime("%-d %B %Y")
    amount_str = f"₹{order.final_amount:,.2f}"
    gupshup.send_whatsapp_transaction_gupshup(
        isd_code=current_user.isd_code,
        phone_number=current_user.phone_number,
        name=current_user.first_name,
        amount=amount_str,
        valid=valid_date,
        plan="PRO"
    )

    # Referral credit only for first paid plan
    if current_user.referred_by:
        add_credit(
            db=db,
            user_id=current_user.referred_by,
            source_user_id=current_user.id,
            credit_type=CreditType.REFERRAL_USER,
            meta={"reason": "User subscribed to plan", "plan_id": 1}
        )

    db.flush()

def add_credit(
    db: Session,
    user_id: int,
    source_user_id: int,
    credit_type: CreditType = None,
    meta: dict = None
):
    # --- Fetch user ---
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise Exception("user_not_found")

    # --- Calculate credit amount ---
    amount, credit_type = calculate_credit_amount(db, user, source_user_id, credit_type)

    # --- Apply credit for user ---
    new_credit = apply_credit(
        db=db,
        user_id=user.id,
        source_user_id=source_user_id,
        amount=amount,
        credit_type=credit_type,
        meta=meta
    )

    # --- Handle parent commission (if needed) ---
    if user.role == RoleTypeEnum.SALES and user.parent_user_id:
        add_parent_commission(db, user, source_user_id, meta)

    # --- Commit and notify ---
    db.commit()
    send_credit_notification(db,user.id, amount)

    return new_credit

def calculate_credit_amount(db: Session, user: User, source_user_id: int, credit_type: CreditType):
    if user.role == RoleTypeEnum.ADMIN or user.role == RoleTypeEnum.EMPLOYEE:
        return 150.0, credit_type

    if user.role in [RoleTypeEnum.PLATFORM_ADMIN, RoleTypeEnum.SALES]:
        source_order = (
            db.query(UserOrder)
            .filter(
                UserOrder.user_id == source_user_id,
                UserOrder.status == OrderStatus.COMPLETED
            )
            .order_by(UserOrder.created_at.desc())
            .first()
        )
        if not source_order:
            raise Exception("source_user_no_completed_order")

        # --- CASE 1: ADMIN / EMPLOYEE (fixed credit, no % logic) ---
        if user.role in [RoleTypeEnum.ADMIN, RoleTypeEnum.EMPLOYEE]:
            return 150.0, credit_type

        # --- CASE 2: PLATFORM ADMIN ---
        if user.role == RoleTypeEnum.PLATFORM_ADMIN:
            if source_order.type == OrderType.REGISTRATION:  # new user plan
                percentage = 0.25
            else:  # add-ons or renewals
                percentage = 0.10
            return round(source_order.final_amount * percentage, 2), CreditType.REFERRAL_PLATFORM

        # --- CASE 3: SALES ---
        if user.role == RoleTypeEnum.SALES:
            if source_order.type == OrderType.REGISTRATION:
                percentage = 0.20
            else:  # add-ons or renewals
                percentage = 0.05
            return round(source_order.final_amount * percentage, 2), CreditType.REFERRAL_PLATFORM

        # --- Default ---
        return 0.0, credit_type

    # default
    return 0.0, credit_type

def apply_credit(db: Session, user_id: int, source_user_id: int, amount: float, credit_type: CreditType, meta: dict):
    last_credit = (
        db.query(UserCredit)
        .filter(UserCredit.user_id == user_id)
        .order_by(UserCredit.created_at.desc())
        .first()
    )
    previous_balance = last_credit.balance_after if last_credit else 0.0

    new_credit = UserCredit(
        user_id=user_id,
        source_user_id=source_user_id,
        amount=amount,
        type=credit_type,
        code_used=None,  # can add if needed
        meta=meta or {},
        balance_after=previous_balance + amount
    )

    db.add(new_credit)
    return new_credit

def add_parent_commission(db: Session, user: User, source_user_id: int, meta: dict):
    parent_user = db.query(User).filter(User.id == user.parent_user_id).first()
    if not parent_user:
        return

    source_order = (
        db.query(UserOrder)
        .filter(UserOrder.user_id == source_user_id, UserOrder.status == OrderStatus.COMPLETED)
        .order_by(UserOrder.created_at.desc())
        .first()
    )
    if not source_order:
        return

    parent_credit_amount = round(source_order.final_amount * 0.05, 2)
    apply_credit(
        db=db,
        user_id=parent_user.id,
        source_user_id=source_user_id,
        amount=parent_credit_amount,
        credit_type=CreditType.REFERRAL_PARENT,
        meta={"reason": "Child sales commission", **(meta or {})}
    )

def send_credit_notification(db:Session,user_id: int, amount: float):
    try:
        asyncio.run(send_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.ORDER,
                message=f"You have been credited ₹{amount}",
                url=None
            )
        ))
    except Exception as e:
        print(f"Notification error: {str(e)}")
