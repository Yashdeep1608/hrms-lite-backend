


#Create Order
from datetime import datetime, timedelta, timezone
import json
import uuid
import razorpay
from requests import Session

from app.models.coupon import Coupon
from app.models.enums import CreditType, OrderStatus, PaymentMode, PaymentStatus, PlanStatus
from app.models.plan import Plan
from app.models.user import User, UserCredit, UserOrder, UserPayment, UserPlan
from app.schemas.payment import CreateOrder, PlaceOrder, RazorpayPaymentVerify
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
            subtotal = offer_discount - coupon_discount
        
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

        gst_percent = 18.0
        gst_amount = round(subtotal * gst_percent / 100, 2)
        final_amount = subtotal + gst_amount

        return {
            "user_id": order.user_id,
            "plan_id": order.plan_id or None,
            "total": total_price,
            "offer_discount": offer_discount,
            "coupon_discount": coupon_discount,
            "gst_percent": gst_percent,
            "gst_amount": gst_amount,
            "subtotal": subtotal,
            "final_amount": final_amount,
        }

    except Exception as e:
        raise e
    
def place_order(db: Session, payload: PlaceOrder):
    try:
        if not payload.user_id:
            raise Exception("user_required")

        user_order = UserOrder(
            user_id=payload.user_id,
            business_id=payload.business_id,
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
                    credit_type=CreditType.REFERRAL_USER,    # or COUPON_REFERRAL based on logic
                    code_used=new_user.referral_code,        # or coupon code
                    meta={"reason": "User subscribed to plan", "plan_id": order.plan_id}
                )
            elif order and order.coupon_code:
                coupon = db.query(Coupon).filter(Coupon.code == order.coupon_code).first();
                if coupon and coupon.user_id:
                    add_credit(
                    db=db,
                    user_id=coupon.user_id,            # Referrer gets credit
                    source_user_id=new_user.id,              # This new user caused it
                    credit_type=CreditType.COUPON_REFERRAL,    # or COUPON_REFERRAL based on logic
                    code_used=order.coupon_code,        # or coupon code
                    meta={"reason": "User subscribed to plan", "plan_id": order.plan_id}
                )
    db.commit()
    return payment

def add_credit(
    db: Session,
    *,
    user_id: int,
    source_user_id: int,
    credit_type: CreditType,
    code_used: str = None,
    meta: dict = None
):
    amount = 0.0
    if credit_type == CreditType.REFERRAL_USER:
        amount = 500.0
    if credit_type == CreditType.COUPON_REFERRAL:
        if meta["plan_id"] == 1:
            amount = 1500.0
        if meta["plan_id"] == 2:
            amount = 2800.0
    # Optional: Fetch last balance if needed (or use 0)
    last_credit = (
        db.query(UserCredit)
        .filter(UserCredit.user_id == source_user_id)
        .order_by(UserCredit.created_at.desc())
        .first()
    )
    previous_balance = last_credit.balance_after or 0.0

    new_credit = UserCredit(
        user_id=user_id,             # who gets the credit
        source_user_id=source_user_id,             # who triggered it (new user)
        amount=amount,
        type=credit_type,
        code_used=code_used,
        meta=meta or {},
        balance_after=previous_balance + amount,
    )

    db.add(new_credit)
    db.commit()
    db.refresh(new_credit)
    return new_credit

#  Webhook for payment status updates (to catch refunds, late confirmations)

#  Email/notification upon successful payment

#  Admin panel to monitor transactions and plans

#  Retry logic if payment fails before confirmation