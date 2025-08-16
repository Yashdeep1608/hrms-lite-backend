#Create Order
import asyncio
from datetime import datetime, timedelta, timezone
import json
import razorpay
from requests import Session

from app.models.coupon import Coupon
from app.models.enums import CreditType, OrderStatus, PaymentMode, PaymentStatus, PlanStatus, RoleTypeEnum
from app.models.notification import NotificationType
from app.models.plan import Plan
from app.models.user import User, UserCredit, UserOrder, UserPayment, UserPlan
from app.schemas.notification import NotificationCreate
from app.schemas.payment import CreateOrder, PlaceOrder, RazorpayPaymentVerify
from app.services.notifications.notification_service import send_notification
from app.services.payments.razorpay_service import create_razorpay_order, fetch_razorpay_payment


def create_order(db: Session, order: CreateOrder):
    try:
        if not order.user_id:
            raise Exception("user_required")

        plan = None
        offer_discount = 0.0
        coupon_discount = 0.0
        total_price = 0.0
        subtotal = 0.0

        
        # Plan logic
        if order.plan_id:
            plan = db.query(Plan).filter(Plan.id == order.plan_id).first()
            if not plan:
                raise Exception("plan_not_found")

            offer_discount = plan.offer_discount or 0.0
            total_price = plan.price
            subtotal = total_price - offer_discount - coupon_discount
        
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

        # gst_percent = 18.0
        # gst_amount = round(subtotal * gst_percent / 100, 2)
        final_amount = subtotal

        return {
            "user_id": order.user_id,
            "plan_id": order.plan_id or None,
            "total": total_price,
            "offer_discount": offer_discount,
            "coupon_discount": coupon_discount,
            "gst_percent": 0,
            "gst_amount": 0,
            "subtotal": subtotal,
            "final_amount": final_amount,
        }

    except Exception as e:
        raise e
    
def place_order(db: Session, payload: PlaceOrder):
    try:
        if not payload.user_id:
            raise Exception("user_required")
        user = db.query(User).filter(User.id == payload.user_id).first()
        user_order = UserOrder(
            user_id=payload.user_id,
            business_id=user.business_id if user else None,
            plan_id=payload.plan_id or None,
            coupon_code=payload.coupon_code or None,
            order_type=payload.order_type,
            original_amount=payload.original_amount,
            offer_discount=payload.offer_discount,
            coupon_discount=payload.coupon_discount,
            subtotal=payload.subtotal,
            gst_percent=18.0,
            gst_amount=payload.gst_amount,
            final_amount=payload.final_amount,
            notes=payload.notes,
            status=OrderStatus.CREATED
        )

        db.add(user_order)
        db.commit()
        db.refresh(user_order)
        try:
            receipt_id = str(user_order.id)
            razorpay_order = create_razorpay_order(
                amount=user_order.final_amount,
                currency="INR",
                receipt=receipt_id,
                notes={"user_id": str(payload.user_id), "order_type": payload.order_type or "general"}
            )

            # Save razorpay_order_id to DB
            user_order.razorpay_order_id = razorpay_order["id"]
            notes={"user_id": str(payload.user_id), "order_type": payload.order_type or "general"}
            notes_str = json.dumps(notes)
            user_payment = UserPayment(
                user_id=payload.user_id,
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
        except razorpay.errors.BadRequestError as e:
            db.rollback()
            if "invalid api key" in str(e).lower():
                raise Exception("Razorpay authentication failed. Check API keys.")
            raise Exception(f"Razorpay BadRequestError: {str(e)}")

        except razorpay.errors.ServerError as e:
            db.rollback()
            raise Exception("Razorpay server error, please try again later.")

        except razorpay.errors.SignatureVerificationError as e:
            db.rollback()
            raise Exception("Signature verification failed.")

        except Exception as e:
            db.rollback()
            raise Exception(f"Failed to create Razorpay order: {str(e)}")

    except Exception as e:
        db.rollback()
        raise e
    
def verify_user_payment(
    db: Session,payload:RazorpayPaymentVerify):
    payment = db.query(UserPayment).filter(
            UserPayment.razorpay_order_id == payload.order_id
        ).first()

    if not payment:
        raise Exception("payment_not_found")
    payment_data = fetch_razorpay_payment(payload.payment_id)
    payment_status = payment_data.get("status")  # captured, failed, refunded, authorized, etc.
    payment_method = payment_data.get("method", "unknown")
    payment.razorpay_payment_id = payload.payment_id
    payment.payment_method = payment_method
    payment.is_verified = True
    # Update payment status based on Razorpay
    if payment_status == "captured":
        payment.status = PaymentStatus.SUCCESS
    elif payment_status =="failed":
        payment.status = PaymentStatus.FAILED
    elif payment_status =="refunded":
        payment.status = PaymentStatus.REFUNDED
    elif payment_status == "authorized":
        payment.status = PaymentStatus.PENDING
    else:
        payment.status = PaymentStatus.FAILED  # fallback

    # Update associated order as well
    order = db.query(UserOrder).filter(UserOrder.razorpay_order_id == payload.order_id).first()
    if order:
        if payment.status == PaymentStatus.SUCCESS:
            order.status = OrderStatus.COMPLETED
        elif payment.status == PaymentStatus.FAILED:
            order.status = OrderStatus.FAILED
        elif payment.status == PaymentStatus.REFUNDED:
            order.status = OrderStatus.REFUNDED
        elif payment.status == PaymentStatus.PENDING:
            order.status = OrderStatus.PENDING
    
    # ✅ If payment completed and plan_id exists, create UserPlan
    if payment.status == PaymentStatus.SUCCESS and order.plan_id:
        plan = db.query(Plan).filter(Plan.id == order.plan_id).first()

        if not plan:
            raise Exception("plan_not_found")

        existing_plan = db.query(UserPlan).filter(
            UserPlan.user_id == order.user_id
        ).first()

        now = datetime.now(timezone.utc)
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)

        # End of the Nth day (inclusive): 23:59:59.999999
        end_date = (start_date + timedelta(days=plan.duration_days or 30)).replace(
            hour=23, minute=59, second=59, microsecond=999999
        )

        if existing_plan:
            # ✅ Update existing plan
            existing_plan.payment_id = payment.id
            existing_plan.start_date = start_date
            existing_plan.end_date = end_date
            existing_plan.status = PlanStatus.ACTIVE
            existing_plan.is_trial = False
            db.commit()
            db.refresh(existing_plan)
        else:
            # ✅ Create new plan
            new_user_plan = UserPlan(
                user_id=order.user_id,
                plan_id=order.plan_id,
                payment_id=payment.id,
                start_date=start_date,
                end_date=end_date,
                status=PlanStatus.ACTIVE,
                is_trial=False
            )
            db.add(new_user_plan)
            new_user = db.query(User).filter(User.id == order.user_id).first()
            if new_user and new_user.referred_by:
                add_credit(
                    db=db,
                    user_id=new_user.referred_by,            # Referrer gets credit
                    source_user_id=new_user.id,              # This new user caused it
                    credit_type=CreditType.REFERRAL_USER,    # logic
                    meta={"reason": "User subscribed to plan", "plan_id": order.plan_id}
                )
    db.commit()
    return payment

def add_credit(
    db: Session,
    user_id: int,
    source_user_id: int,
    credit_type: CreditType = None,
    code_used: str = None,
    meta: dict = None
):
    # Fetch the user to check role if needed
    user = db.query(User).filter(User.id == user_id).first()
    code_used = user.referral_code
    if not user:
        raise Exception("user_not_found")

    # Flat credit amount for any eligible user
    amount = 100.0

    # Optional: you can adjust based on role
    # Example:  
    if user.role == RoleTypeEnum.ADMIN:
        amount = 200.0
    elif user.role == RoleTypeEnum.EMPLOYEE:
        amount = 100.0
    elif user.role == RoleTypeEnum.PLATFORM_ADMIN:
        # Get source user's last completed order
        credit_type = CreditType.REFERRAL_PLATFORM
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
        
        percentage = 0.4 if source_order.final_amount < 10000 else 0.3
        amount = round(source_order.final_amount * percentage, 2)

    elif user.role == RoleTypeEnum.SALES:
        credit_type = CreditType.REFERRAL_PLATFORM
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
        
        percentage = 0.25 if source_order.final_amount < 10000 else 0.2
        amount = round(source_order.final_amount * percentage, 2)

    # Get last balance
    last_credit = (
        db.query(UserCredit)
        .filter(UserCredit.user_id == source_user_id)
        .order_by(UserCredit.created_at.desc())
        .first()
    )
    previous_balance = last_credit.balance_after if last_credit and  last_credit.balance_after else 0.0

    new_credit = UserCredit(
        user_id=user_id,               # who gets the credit
        source_user_id=source_user_id, # who triggered it
        amount=amount,
        type=credit_type,
        code_used=code_used,
        meta=meta or {},
        balance_after=previous_balance + amount,
    )
    try:
        asyncio.run(send_notification(
            db,
            NotificationCreate(
                user_id=user_id,
                type=NotificationType.ORDER,
                message=f"Your just credited amount of {amount}",
                url="/dashboard"
            )
        ))
    except Exception as e:
        raise Exception(str(e))
    db.add(new_credit)
    db.commit()
    db.refresh(new_credit)
    return new_credit

#  Webhook for payment status updates (to catch refunds, late confirmations)

#  Email/notification upon successful payment

#  Admin panel to monitor transactions and plans

#  Retry logic if payment fails before confirmation