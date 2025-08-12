import calendar
from datetime import timedelta
from decimal import Decimal
import uuid
from sqlalchemy import case, func, or_
from app.crud.product import add_product_stock_log
from app.models.enums import ProductStockSource, RoleTypeEnum
from app.models.expense import Expense, ExpenseCategory
from app.models.loan import *
from app.models.product import Product
from app.models.supplier import *
from sqlalchemy.orm import Session,joinedload
from app.models.user import User
from app.schemas.expense import *
from app.schemas.loan import *
from app.schemas.supplier import *

def generate_purchase_number(id:int):
    now = datetime.now()
    return f"PRCH-{id}-{now.strftime('%Y%m%d-%H%M%S')}"
def generate_transaction_id():
    short_id = uuid.uuid4().hex[:16].upper()
    return f"SPTXN-{short_id}"
from datetime import date, timedelta
from decimal import Decimal
import calendar
import logging
from sqlalchemy import func

logger = logging.getLogger(__name__)

def _first_of_month(dt: date) -> date:
    return date(dt.year, dt.month, 1)

def _last_of_month(dt: date) -> date:
    last_day = calendar.monthrange(dt.year, dt.month)[1]
    return date(dt.year, dt.month, last_day)

def _safe_repayment_amount(loan) -> Decimal:
    """Return per-EMI amount as Decimal. If loan.repayment_amount missing, try total/emi_number fallback."""
    if loan.repayment_amount is not None:
        return Decimal(str(loan.repayment_amount))
    # fallback: if emi_number exists, divide total_amount_payable / emi_number
    if loan.emi_number:
        total = Decimal(str(loan.total_amount_payable or 0))
        return (total / Decimal(str(loan.emi_number))).quantize(Decimal("0.01"))
    return Decimal("0.00")


def generate_repayments(db: Session, loan: Loan):
    """
    Generate (idempotently) repayments for:
      - an aggregated PAID record covering [start_date .. yesterday] if none exist in that range
      - a PENDING record for today (if due)
      - PENDING records for the rest of current month (tomorrow..month_end) according to frequency

    Notes:
      - Only for DAILY / WEEKLY / MONTHLY. Skips BULLET / FLEXIBLE / NO_COST.
      - This function will not create records beyond current month.
      - It will not modify existing repayments (only insert missing ones).
    """
    # Skip types that should not auto-generate
    if loan.repayment_type in (LoanRepaymentType.FLEXIBLE, LoanRepaymentType.NO_COST, LoanRepaymentType.BULLET):
        return

    try:
        today = date.today()
        month_start = _first_of_month(today)
        month_end = _last_of_month(today)

        # If loan starts after the end of this month, nothing to generate
        if loan.start_date > month_end:
            return

        per_emi = _safe_repayment_amount(loan)

        # Determine existing payment dates for this loan in the month and past region
        existing_dates_all = {
            row[0] for row in db.query(LoanRepayment.payment_date)
                                .filter(LoanRepayment.loan_id == loan.id).all()
        }

        # -----------------------------
        # 1) Aggregated "PAID" for past (start_date -> yesterday)
        # -----------------------------
        past_end = today - timedelta(days=1)
        if loan.end_date and loan.end_date < past_end:
            past_end = loan.end_date

        if past_end >= loan.start_date:
            # Only create aggregated past if **no** repayment exists in that entire past range
            cnt_existing_in_past = db.query(LoanRepayment).filter(
                LoanRepayment.loan_id == loan.id,
                LoanRepayment.payment_date >= loan.start_date,
                LoanRepayment.payment_date <= past_end
            ).count()

            if cnt_existing_in_past == 0:
                # compute how many installments and how much total for that period
                installments = 0
                total_amount = Decimal("0.00")

                if loan.repayment_type == LoanRepaymentType.DAILY:
                    days = (past_end - loan.start_date).days + 1
                    installments = days
                    total_amount = per_emi * Decimal(days)

                elif loan.repayment_type == LoanRepaymentType.WEEKLY:
                    # count occurrences of repayment weekday between start_date and past_end (inclusive)
                    target_weekday = loan.repayment_day or loan.start_date.isoweekday()
                    d = loan.start_date
                    while d <= past_end:
                        if d.isoweekday() == target_weekday:
                            installments += 1
                        d += timedelta(days=1)
                    total_amount = per_emi * Decimal(installments)

                elif loan.repayment_type in [LoanRepaymentType.MONTHLY,LoanRepaymentType.NO_COST,LoanRepaymentType.BULLET]:
                    # iterate month by month and count months whose scheduled day falls in range
                    y = loan.start_date.year
                    m = loan.start_date.month
                    while True:
                        dim = calendar.monthrange(y, m)[1]
                        day = loan.repayment_day if loan.repayment_day and loan.repayment_day <= dim else dim
                        candidate = date(y, m, day)
                        if candidate >= loan.start_date and candidate <= past_end:
                            installments += 1
                        # advance one month
                        if candidate > past_end:
                            break
                        # move to next month
                        if m == 12:
                            y += 1
                            m = 1
                        else:
                            m += 1
                        # stop if we've moved beyond past_end month
                        if date(y, m, 1) > past_end:
                            # still need to check the month we entered (loop handles candidate)
                            pass
                    total_amount = per_emi * Decimal(installments)

                # Insert aggregated PAID record only if there is at least one installment
                if installments > 0 and total_amount > Decimal("0.00"):
                    aggregated_note = f"Aggregated {installments} installment(s) from {loan.start_date.isoformat()} to {past_end.isoformat()}"
                    agg = LoanRepayment(
                        loan_id=loan.id,
                        payment_date=past_end,
                        amount_paid=total_amount.quantize(Decimal("0.01")),
                        status=LoanRepaymentStatus.PAID,
                        notes=aggregated_note
                    )
                    # ensure not duplicate date (just in case)
                    if agg.payment_date not in existing_dates_all:
                        db.add(agg)
                        db.commit()
                        # refresh existing dates set
                        existing_dates_all.add(agg.payment_date)

        # -----------------------------
        # 2) Create PENDING for today if due (and none exists)
        # -----------------------------
        def _is_due_on(d: date) -> bool:
            if d < loan.start_date:
                return False
            if loan.end_date and d > loan.end_date:
                return False

            if loan.repayment_type == LoanRepaymentType.DAILY:
                return True
            if loan.repayment_type == LoanRepaymentType.WEEKLY:
                target = loan.repayment_day or d.isoweekday()
                return (d.isoweekday() == target)
            if loan.repayment_type in [LoanRepaymentType.MONTHLY,LoanRepaymentType.NO_COST,LoanRepaymentType.BULLET]:
                dim = calendar.monthrange(d.year, d.month)[1]
                day = loan.repayment_day if loan.repayment_day and loan.repayment_day <= dim else dim
                return d.day == day
            return False

        inserts = []
        if _is_due_on(today) and today not in existing_dates_all:
            inserts.append(
                LoanRepayment(
                    loan_id=loan.id,
                    payment_date=today,
                    amount_paid=per_emi.quantize(Decimal("0.01")),
                    status=LoanRepaymentStatus.PENDING,
                    notes="Auto-generated: today due"
                )
            )
            existing_dates_all.add(today)

        # -----------------------------
        # 3) Create PENDING for the rest of the current month (tomorrow .. month_end)
        # -----------------------------
        cursor = today + timedelta(days=1)
        while cursor <= month_end:
            # stop if beyond loan end_date
            if loan.end_date and cursor > loan.end_date:
                break

            if _is_due_on(cursor) and cursor not in existing_dates_all:
                inserts.append(
                    LoanRepayment(
                        loan_id=loan.id,
                        payment_date=cursor,
                        amount_paid=per_emi.quantize(Decimal("0.01")),
                        status=LoanRepaymentStatus.PENDING,
                        notes="Auto-generated: current month schedule"
                    )
                )
                existing_dates_all.add(cursor)

            cursor += timedelta(days=1)

        # Bulk insert if any
        if inserts:
            db.add_all(inserts)
            db.commit()

    except Exception as exc:
        # Rollback any partial work and re-raise so caller can decide to ignore
        try:
            db.rollback()
        except Exception:
            logger.exception("Rollback failed while handling generate_repayments error.")
        logger.exception("generate_repayments failed for loan_id=%s: %s", getattr(loan, "id", None), exc)
        raise

def create_expense(db: Session, payload: AddEditExpense,current_user:User):
    expense = Expense(
        business_id=current_user.business_id,
        created_by_user_id =current_user.id,
        category_id=payload.category_id,
        expense_date=payload.expense_date,
        amount =payload.amount,
        notes = payload.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

def update_expense(db: Session, expense_id: int, payload: AddEditExpense):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    expense.category_id = payload.category_id
    expense.expense_date = payload.expense_date
    expense.amount = payload.amount
    expense.notes = payload.notes
    db.commit()
    db.refresh(expense)
    return expense

def get_expense_by_id(db: Session, expense_id: int):
    return db.query(Expense).filter(Expense.id == expense_id).first()

def get_expenses(db: Session, filters: ExpenseFilters, current_user: User):
    query = db.query(Expense).options(
        joinedload(Expense.category)  # eager load category
    )

    if filters.category_id:
        query = query.filter(Expense.category_id == filters.category_id)
    if filters.search:
        query = query.filter(or_(Expense.notes.ilike(f"%{filters.search}%"),))
    if filters.from_date:
        query = query.filter(Expense.expense_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(Expense.expense_date <= filters.to_date)

    # Role restriction
    if current_user.role not in [RoleTypeEnum.ADMIN, RoleTypeEnum.SUPERADMIN, RoleTypeEnum.PLATFORM_ADMIN]:
        query = query.filter(Expense.created_by_user_id == current_user.id)

    total = query.count()

    # Sorting
    sort_attr = getattr(Expense, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Pagination
    skip = (filters.page - 1) * filters.page_size
    expenses = query.offset(skip).limit(filters.page_size).all()

    # Format output with category info
    items = [
        {
            "id": exp.id,
            "business_id": exp.business_id,
            "category_id": exp.category_id,
            "amount": float(exp.amount),
            "notes": exp.notes,
            "expense_date": exp.expense_date,
            "created_at": exp.created_at,
            "updated_at": exp.updated_at,
            "category_name": exp.category.name if exp.category else None,
            "image_url": exp.category.image_url if exp.category else None
        }
        for exp in expenses
    ]

    return {
        "items": items,
        "total": total
    }

def delete_expense(db: Session, expense_id: int):
    expense = db.get(Expense,expense_id)
    if not expense: 
        raise Exception("Expense not found")
    db.delete(expense)
    db.commit()

def get_expense_categories(db:Session):
    return db.query(ExpenseCategory).all()

def create_loan(db: Session, payload: AddEditLoan,current_user:User):
    loan = Loan(
        business_id=current_user.business_id,
        lender_name = payload.lender_name,
        lender_contact = payload.lender_contact,
        principal_amount = payload.principal_amount,
        interest_rate = payload.interest_rate,
        total_amount_payable = payload.total_amount_payable,
        repayment_type = payload.repayment_type,
        repayment_amount = payload.repayment_amount,
        repayment_day = payload.repayment_day,
        emi_number = payload.emi_number,
        start_date = payload.start_date,
        end_date = payload.end_date,
        notes = payload.notes,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
    
    # Only generate repayments for the current month
    if loan.repayment_type in [LoanRepaymentType.DAILY, LoanRepaymentType.WEEKLY, LoanRepaymentType.MONTHLY, LoanRepaymentType.NO_COST]:
        generate_repayments(db, loan)
    if loan.repayment_type == LoanRepaymentType.BULLET:
        loan_repayment = LoanRepayment(
            loan_id=loan.id,
            amount_paid=loan.total_amount_payable,
            payment_date = loan.end_date,
            status=LoanRepaymentStatus.PENDING,
            notes="Auto-generated"
        )
        db.add(loan_repayment)
        db.commit()
    return loan

def update_loan(db: Session, loan_id: int, payload: AddEditExpense):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    
    if not loan:
        raise Exception("loan_not_found")
    
    data_dict = payload.model_dump(exclude_unset=True)

    for field, value in data_dict.items():
            if hasattr(loan, field):
                setattr(loan, field, value)

    db.commit()
    db.refresh(loan)
    return loan

def get_loan_by_id(db: Session, loan_id: int):
    today = date.today()

    # Preload repayments to avoid N+1 queries
    loan = (
        db.query(Loan)
        .options(joinedload(Loan.repayments).joinedload(LoanRepayment.loan))
        .filter(Loan.id == loan_id)
        .first()
    )

    if not loan:
        return None

    # Only generate if first call of the month
    last_repayment = (
        db.query(LoanRepayment)
        .filter(LoanRepayment.loan_id == loan_id)
        .order_by(LoanRepayment.payment_date.desc())
        .first()
    )

    if not last_repayment or last_repayment.payment_date.month != today.month or last_repayment.payment_date.year != today.year:
        generate_repayments(db, loan)

    # ---- Total Paid ----
    total_paid = sum(
        float(r.amount_paid)
        for r in loan.repayments
        if r.status == LoanRepaymentStatus.PAID
    )
    remaining_amount = max(float(loan.total_amount_payable) - total_paid, 0)

    # ---- EMI Details ----
    emi_amount = float(loan.repayment_amount or 0)
    total_installments = (
        int(float(loan.total_amount_payable) // emi_amount) if emi_amount else None
    )

    remaining_installments = None
    if emi_amount:
        remaining_installments = int(remaining_amount // emi_amount)
        if remaining_amount % emi_amount > 0:
            remaining_installments += 1

    # ---- Last Payment Date ----
    paid_repayments = [r for r in loan.repayments if r.status == LoanRepaymentStatus.PAID]
    last_payment_date = max((r.payment_date for r in paid_repayments), default=None)

    # ---- Next Due Date ----
    base_date = last_payment_date or loan.start_date
    next_due_date = None

    if loan.repayment_type == LoanRepaymentType.DAILY:
        next_due_date = (last_payment_date or loan.start_date) + timedelta(days=1)

    elif loan.repayment_type == LoanRepaymentType.WEEKLY:
        base_date = last_payment_date or loan.start_date
        # Move forward exactly 1 week from last payment date
        next_due_date = base_date + timedelta(days=7)

    elif loan.repayment_type == LoanRepaymentType.MONTHLY or loan.repayment_type == LoanRepaymentType.NO_COST:
        base_date = last_payment_date or loan.start_date
        day = min(loan.repayment_day, 28)  # avoid invalid dates
        month = base_date.month
        year = base_date.year

        # Always move to the *next month*
        if month == 12:
            month = 1
            year += 1
        else:
            month += 1

        next_due_date = date(year, month, day)

    elif loan.repayment_type == LoanRepaymentType.BULLET:
        # Only one due date: loan end date
        next_due_date = loan.end_date

    elif loan.repayment_type == LoanRepaymentType.FLEXIBLE:
        # No strict schedule, due date could be next month start
        next_due_date = None  # Optional: Or keep it empty for frontend

    # ---- Auto-Close Loan ----
    if remaining_amount <= 0 and loan.status != LoanStatus.CLOSED:
        loan.status = LoanStatus.CLOSED
        db.commit()

    # ---- Frontend Repayments ----
    repayment_list = [
        {
            "id": r.id,
            "payment_date": r.payment_date,
            "amount_paid": float(r.amount_paid),
            "notes": r.notes,
            "status": r.status,
        }
        for r in loan.repayments
    ]
    repayment_list.sort(key=lambda x: x["payment_date"])

    return {
        "loan_id": loan.id,
        "lender_name": loan.lender_name,
        "lender_contact": loan.lender_contact,
        "notes": loan.notes,
        "loan_amount": float(loan.total_amount_payable),
        "principal_amount": float(loan.principal_amount),
        "repayment_type": loan.repayment_type,
        "repayment_day": loan.repayment_day,
        "total_amount_payable": loan.total_amount_payable,
        "repayment_amount": emi_amount,
        "emi_number": loan.emi_number,
        "total_installments": total_installments,
        "total_paid": total_paid,
        "remaining_amount": remaining_amount,
        "remaining_installments": remaining_installments,
        "progress_percent": round((total_paid / float(loan.total_amount_payable)) * 100, 2)
            if loan.total_amount_payable else 0,
        "last_payment_date": last_payment_date,
        "next_due_date": next_due_date,
        "status": loan.status,
        "overdue_days": (
            (today - next_due_date).days
            if next_due_date and next_due_date < today and loan.status != LoanStatus.CLOSED
            else 0
        ),
        "is_fully_paid": remaining_amount <= 0,
        "start_date": loan.start_date,
        "end_date": loan.end_date,
        "interest_rate": loan.interest_rate,
        "repayments": repayment_list,
    }

def get_loans(db: Session,filters:LoanFilters,current_user:User):
    query = db.query(Loan)

    if filters.search:
        query = query.filter(or_(Loan.notes.like(f"%{filters.search}%"),))
    if filters.status:
        query = query.filter(Loan.status == filters.status)
    if filters.from_date:
        query = query.filter(Loan.created_at >= filters.from_date)
    if filters.to_date:
        query = query.filter(Loan.created_at <= filters.to_date)
    
    total = query.count()
    sort_attr = getattr(Loan, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Count and paginate
    skip = (filters.page - 1) * filters.page_size
    items = query.offset(skip).limit(filters.page_size).all()
    # Pagination
    return {
        "items":items,
        "total":total
    }

def delete_loan(db: Session, loan_id: int):
    loan = db.get(Loan,loan_id)
    if not loan: 
        raise Exception("loan_not_found")
    db.delete(loan)
    db.commit()

def get_loan_repayment_reminders(db: Session, current_user: User):
    today = date.today()
    reminders = []

    loans = db.query(Loan).filter(
        Loan.business_id == current_user.business_id,
        Loan.status == LoanStatus.ACTIVE
    ).all()

    for loan in loans:
        # Fetch only unpaid repayments
        repayments = db.query(LoanRepayment).filter(
            LoanRepayment.loan_id == loan.id,
            LoanRepayment.status != LoanRepaymentStatus.PAID
        ).order_by(LoanRepayment.payment_date.asc()).all()

        # --- Generate reminders ---
        for r in repayments:
            if r.payment_date == today:
                reminders.append(
                    f"Loan '{loan.lender_name}' – Repayment of ₹{loan.repayment_amount} is due today."
                )
            elif r.payment_date < today:
                reminders.append(
                    f"Loan '{loan.lender_name}' – Repayment of ₹{loan.repayment_amount} was overdue on {r.payment_date}."
                )

        # Special cases
        if loan.repayment_type == LoanRepaymentType.BULLET and loan.end_date and today >= loan.end_date - timedelta(days=3):
            reminders.append(
                f"Loan '{loan.lender_name}' – Full repayment of ₹{loan.total_amount_payable} is due on {loan.end_date}."
            )

        if loan.repayment_type == LoanRepaymentType.FLEXIBLE:
            last_paid = db.query(LoanRepayment).filter(
                LoanRepayment.loan_id == loan.id,
                LoanRepayment.status == LoanRepaymentStatus.PAID
            ).order_by(LoanRepayment.payment_date.desc()).first()

            if not last_paid or (today - last_paid.payment_date).days >= 30:
                reminders.append(
                    f"Loan '{loan.lender_name}' – Flexible loan: consider making a payment."
                )

        if loan.repayment_type == LoanRepaymentType.NO_COST and loan.end_date and today >= loan.end_date - timedelta(days=3):
            reminders.append(
                f"Loan '{loan.lender_name}' – No-cost loan ends on {loan.end_date}."
            )

    return reminders

def add_loan_repayment(db: Session, payload: LoanRepaymentRequest):
    # Fetch loan
    loan = db.query(Loan).filter(Loan.id == payload.loan_id).first()
    if not loan:
        raise Exception("loan_not_found")

    # Ensure Decimal amounts
    payment_amount = Decimal(str(payload.payment_amount or 0))
    total_amount_payable = Decimal(str(loan.total_amount_payable or 0))

    # Total already paid
    total_paid = db.query(func.coalesce(func.sum(LoanRepayment.amount_paid), 0)) \
                   .filter(LoanRepayment.loan_id == loan.id,
                           LoanRepayment.status == LoanRepaymentStatus.PAID) \
                   .scalar() or Decimal("0")
    total_paid = Decimal(str(total_paid))

    # -------------------------
    # CASE 1: repayment_id present → Just mark repayment as paid
    # -------------------------
    if payload.repayment_id:
        loan_repayment = db.query(LoanRepayment).filter(
            LoanRepayment.id == payload.repayment_id,
            LoanRepayment.loan_id == loan.id
        ).first()
        if not loan_repayment:
            raise Exception("loan_repayment_not_found")

        # Just mark as paid, no overpayment check
        loan_repayment.status = LoanRepaymentStatus.PAID
        loan_repayment.notes = payload.notes or "Loan repayment marked as paid"

        db.commit()
        return loan_repayment

    # -------------------------
    # CASE 2: repayment_id not present → Flexible/manual repayment
    # -------------------------

    # Overpayment validation (for flexible payments)
    if total_paid + payment_amount > total_amount_payable:
        raise Exception("payment_exceeds_total_amount")

    # Create new repayment record
    loan_repayment = LoanRepayment(
        loan_id=loan.id,
        payment_date=payload.payment_date,
        amount_paid=payment_amount,
        status=LoanRepaymentStatus.PAID,
        notes=payload.notes or "Loan repayment"
    )
    db.add(loan_repayment)
    db.commit()

    # -------------------------
    # Adjust pending repayments if overpaying EMI amount
    # -------------------------
    scheduled_repayment = Decimal(str(loan.repayment_amount or 0))
    overpay_amount = Decimal("0")

    if scheduled_repayment > 0 and payment_amount > scheduled_repayment:
        overpay_amount = payment_amount - scheduled_repayment

    # Apply overpayment only if all EMIs are generated
    generated_count = db.query(LoanRepayment).filter(
        LoanRepayment.loan_id == loan.id
    ).count()

    if overpay_amount > 0 and generated_count == loan.emi_number:
        pending_repayments = db.query(LoanRepayment) \
            .filter(LoanRepayment.loan_id == loan.id,
                    LoanRepayment.status == LoanRepaymentStatus.PENDING) \
            .order_by(LoanRepayment.payment_date.desc()) \
            .all()

        for r in pending_repayments:
            if overpay_amount <= 0:
                break

            amt = Decimal(str(r.amount_paid or 0))
            if amt <= overpay_amount:
                overpay_amount -= amt
                db.delete(r)
            else:
                r.amount_paid = amt - overpay_amount
                overpay_amount = Decimal("0")
                db.add(r)

        db.commit()

    return loan_repayment

def update_loan_status(db: Session, loan_id: int, status: LoanStatus):
    loan = db.query(Loan).filter(Loan.id == loan_id).first()
    if not loan:
        return None
    loan.status = status
    db.commit()
    db.refresh(loan)
    return loan

def cerate_supplier(db: Session, payload: AddEditSupplier,current_user:User):
    supplier = Supplier(
        business_id=current_user.business_id,
        name = payload.name,
        isd_code = payload.isd_code,
        phone = payload.phone,
        email = payload.email,
        address = payload.address,
        gst_number = payload.gst_number,
        pan_number = payload.pan_number,
        notes = payload.notes
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

def update_supplier(db: Session, supplier_id: int, payload: AddEditSupplier):
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    supplier.name = payload.name
    supplier.isd_code = payload.isd_code
    supplier.phone = payload.phone
    supplier.email = payload.email
    supplier.address = payload.address
    supplier.email = payload.email
    supplier.gst_number = payload.gst_number
    supplier.pan_number = payload.pan_number
    db.commit()
    db.refresh(supplier)
    return supplier

def get_suppliers(db: Session,filters:SupplierFilters,current_user:User):
    query = db.query(Supplier)

    if filters.search:
        query = query.filter(or_(
            Supplier.name.like(f"%{filters.search}%"),
            Supplier.isd_code.like(f"%{filters.search}%"),
            Supplier.phone.like(f"%{filters.search}%"),
            Supplier.email.like(f"%{filters.search}%"),
            Supplier.address.like(f"%{filters.search}%"),
            Supplier.gst_number.like(f"%{filters.search}%"),
            Supplier.pan_number.like(f"%{filters.search}%"),
            ))

    total = query.count()
    sort_attr = getattr(Supplier, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Count and paginate
    skip = (filters.page - 1) * filters.page_size
    items = query.offset(skip).limit(filters.page_size).all()
    # Pagination
    return {
        "items":items,
        "total":total
    }

def delete_supplier(db: Session, supplier_id: int):
    supplier = db.get(Supplier,supplier_id)
    if not supplier: 
        raise Exception("supplier_not_found")
    db.delete(supplier)
    db.commit()

def add_supplier_purchase(db: Session, payload: AddSupplierPurchase,current_user:User):
    # 1️⃣ Create Purchase
    purchase = SupplierPurchase(
        supplier_id=payload.supplier_id,
        purchase_number=generate_purchase_number(payload.supplier_id),
        purchase_date=payload.purchase_date,
        taxable_amount=payload.taxable_amount,
        total_tax_amount=payload.total_tax_amount,
        total_amount=payload.total_amount,
        supplier_invoice_number=payload.supplier_invoice_number,
        file_url=payload.file_url,
        notes=payload.notes
    )
    db.add(purchase)
    db.flush()  # so we have purchase.id without committing
    
    # 2️⃣ Create Purchase Items & Update Products
    for item in payload.items:
        # Create purchase item
        purchase_item = SupplierPurchaseItem(
            purchase_id=purchase.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_price=item.unit_price,
            tax_rate=item.tax_rate,
            tax_amount=item.tax_amount,
            total_amount=item.total_amount
        )
        db.add(purchase_item)

        # Fetch product
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise ValueError(f"Product {item.product_id} not found")

        # Update stock
        old_stock = product.stock_qty or 0
        new_stock = old_stock + float(item.quantity)
        product.stock_qty = new_stock

        # Prepare note details
        changes = [f"Stock-In of {item.quantity} units"]

        # Update tax info (only if tax provided and > 0)
        if item.tax_rate and item.tax_rate > 0:
            old_tax_rate = product.tax_rate
            product.tax_rate = item.tax_rate
            product.include_tax = True
            if old_tax_rate != item.tax_rate:
                changes.append(f"Tax rate updated from {old_tax_rate or 0}% to {item.tax_rate}%")
        
        # Update purchase price (weighted average)
        old_purchase_price = product.purchase_price
        if product.purchase_price:
            total_old_value = float(product.purchase_price) * old_stock
            total_new_value = float(item.unit_price) * float(item.quantity)
            total_qty = old_stock + float(item.quantity)
            product.purchase_price = (total_old_value + total_new_value) / total_qty
        else:
            product.purchase_price = float(item.unit_price)

        if old_purchase_price and round(old_purchase_price, 2) != round(product.purchase_price, 2):
            changes.append(
                f"Purchase price updated from {old_purchase_price} to {round(product.purchase_price, 2)} (weighted avg)"
        )

        # Build final log note
        log_note = f"{'; '.join(changes)} from Supplier Purchase #{purchase.purchase_number}"

        # Add stock log
        add_product_stock_log(
            db=db,
            product_id=product.id,
            quantity=float(item.quantity),
            is_stock_in=True,
            stock_before=old_stock,
            stock_after=new_stock,
            source=ProductStockSource.SUPPLY,
            source_id=purchase.id,
            created_by=current_user.id if current_user else None,
            notes=log_note
        )
    
    # 3️⃣ Create Transactions
    for trx in payload.transactions:
        transaction = SupplierTransaction(
            supplier_id=payload.supplier_id,
            purchase_id=purchase.id,
            transaction_id=generate_transaction_id(),
            transaction_date=trx.transaction_date,
            transaction_type=trx.transaction_type,
            amount=trx.amount,
            payment_method=trx.payment_method
        )
        db.add(transaction)

    # 4️⃣ Commit once
    db.commit()
    db.refresh(purchase)

    return purchase

def add_transactions(db:Session,transactions:List[TransactionRequest]):
    for trx in transactions:
        transaction = SupplierTransaction(
            supplier_id=trx.supplier_id,
            purchase_id=trx.purchase_id,
            transaction_id=generate_transaction_id(),
            transaction_date=trx.transaction_date,
            transaction_type=trx.transaction_type,
            amount=trx.amount,
            payment_method=trx.payment_method
        )
        db.add(transaction)

    # 4️⃣ Commit once
    db.commit()
    return True

def get_supplier_summary(db: Session, supplier_id: int):
    try:
        supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
        if not supplier:
            raise Exception("Supplier not found")

        # Purchase stats
        purchase_stats = db.query(
            func.count(SupplierPurchase.id).label("total_purchases"),
            func.coalesce(func.sum(SupplierPurchase.total_amount), 0).label("total_purchase_amount"),
            func.max(SupplierPurchase.purchase_date).label("last_purchase_date"),
            func.min(SupplierPurchase.purchase_date).label("first_purchase_date"),
            func.avg(SupplierPurchase.total_amount).label("avg_purchase_value"),
            func.max(SupplierPurchase.total_amount).label("largest_purchase")
        ).filter(SupplierPurchase.supplier_id == supplier_id).first()

        # Recent purchase amount
        recent_purchase_amount = db.query(SupplierPurchase.total_amount) \
            .filter(SupplierPurchase.supplier_id == supplier_id) \
            .order_by(SupplierPurchase.purchase_date.desc()) \
            .limit(1).scalar() or 0.0

        transaction_stats = db.query(
            func.count(SupplierTransaction.id).label("total_transactions"),
            func.coalesce(
                func.sum(
                    case(
                        (SupplierTransaction.payment_method != OrderPaymentMethod.CREDIT, SupplierTransaction.amount),
                        else_=0
                    )
                ),
                0
            ).label("total_paid_amount"),
            func.max(SupplierTransaction.transaction_date).label("last_transaction_date"),
        ).filter(
            SupplierTransaction.supplier_id == supplier_id
        ).first()

        # Safe values
        total_purchase_amount = float(getattr(purchase_stats, "total_purchase_amount", 0) or 0)
        total_paid_amount = float(getattr(transaction_stats, "total_paid_amount", 0) or 0)
        total_credit_amount = total_purchase_amount - total_paid_amount
        credit_percentage = (total_credit_amount / total_purchase_amount * 100) if total_purchase_amount else 0

        return {
            "supplier": supplier,
            "total_purchases": getattr(purchase_stats, "total_purchases", 0) or 0,
            "total_purchase_amount": total_purchase_amount,
            "total_paid_amount": total_paid_amount,
            "total_credit_amount": round(total_credit_amount, 2),
            "credit_percentage": round(credit_percentage, 2),
            "total_transactions": getattr(transaction_stats, "total_transactions", 0) or 0,
            "last_purchase_date": getattr(purchase_stats, "last_purchase_date", None),
            "last_transaction_date": getattr(transaction_stats, "last_transaction_date", None),
            "first_purchase_date": getattr(purchase_stats, "first_purchase_date", None),
            "avg_purchase_value": round(float(getattr(purchase_stats, "avg_purchase_value", 0) or 0), 2),
            "largest_purchase": round(float(getattr(purchase_stats, "largest_purchase", 0) or 0), 2),
            "recent_purchase_amount": round(float(recent_purchase_amount), 2),
        }
    except Exception as e:
        raise Exception(str(e))


def get_supplier_purchases(db: Session, filters:SupplierPurchaseFilters):
    query = db.query(SupplierPurchase)
    
    if filters.supplier_id:
        query = query.filter(SupplierPurchase.supplier_id == filters.supplier_id)
    if filters.search:
        query = query.filter(or_(
            SupplierPurchase.purchase_number.like(f"%{filters.search}%")
            ))
    if filters.from_date:
        query = query.filter(SupplierPurchase.purchase_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(SupplierPurchase.purchase_date <= filters.to_date)

    total = query.count()
    sort_attr = getattr(SupplierPurchase, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Count and paginate
    skip = (filters.page - 1) * filters.page_size
    items = query.offset(skip).limit(filters.page_size).all()
    # Pagination
    return {
        "items":items,
        "total":total
    }

def get_supplier_purchase_detail(db: Session, purchase_id:int):
    return db.query(SupplierPurchase).options(joinedload(SupplierPurchase.items)).filter(SupplierPurchase.id == purchase_id).first()

def get_supplier_transactions(db: Session, filters:SupplierTransactionFilters):
    query = db.query(SupplierTransaction)
    if filters.supplier_id:
        query = query.filter(SupplierTransaction.supplier_id == filters.supplier_id)
    if filters.purchase_id:
        query = query.filter(SupplierTransaction.purchase_id == filters.purchase_id)
    if filters.payment_method:
        query = query.filter(SupplierTransaction.payment_method == filters.payment_method)
    if filters.from_date:
        query = query.filter(SupplierTransaction.transaction_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(SupplierTransaction.transaction_date <= filters.to_date)

    total = query.count()
    sort_attr = getattr(SupplierTransaction, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Count and paginate
    skip = (filters.page - 1) * filters.page_size
    items = query.offset(skip).limit(filters.page_size).all()
    # Pagination
    return {
        "items":items,
        "total":total
    }