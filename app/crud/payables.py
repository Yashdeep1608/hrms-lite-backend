from datetime import timedelta
from sqlalchemy import func, or_
from app.models.enums import RoleTypeEnum
from app.models.expense import Expense, ExpenseCategory
from app.models.loan import *
from sqlalchemy.orm import Session,joinedload
from app.models.user import User
from app.schemas.expense import *
from app.schemas.loan import *

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

def get_expenses(db: Session,filters:ExpenseFilters,current_user:User):
    query = db.query(Expense)

    if filters.category_id:
        query = query.filter(Expense.category_id == filters.category_id)
    if filters.search:
        query = query.filter(or_(Expense.notes.like(f"%{filters.search}%"),))
    if filters.from_date:
        query = query.filter(Expense.expense_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(Expense.expense_date <= filters.to_date)
    if current_user.role not in  [RoleTypeEnum.ADMIN,RoleTypeEnum.SUPERADMIN,RoleTypeEnum.PLATFORM_ADMIN]:
        query = query.filter(Expense.created_by_user_id == current_user.id)
    
    total = query.count()
    sort_attr = getattr(Expense, filters.sort_by or "created_at", None)
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
        start_date = payload.start_date,
        end_date = payload.end_date,
        notes = payload.notes,
    )
    db.add(loan)
    db.commit()
    db.refresh(loan)
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
    # Fetch loan with repayments in one query
    loan = (
        db.query(Loan)
        .options(joinedload(Loan.repayments))
        .filter(Loan.id == loan_id)
        .first()
    )
    if not loan:
        return None

    # Calculate totals in Python
    repayments_sorted = sorted(loan.repayments, key=lambda r: r.payment_date, reverse=True)
    total_paid = sum(float(r.amount_paid) for r in loan.repayments)
    remaining_amount = float(loan.total_amount_payable) - total_paid

    # Remaining installments
    remaining_installments = None
    if loan.repayment_amount and loan.repayment_amount > 0:
        remaining_installments = int(remaining_amount // float(loan.repayment_amount))
        if remaining_amount % float(loan.repayment_amount) > 0:
            remaining_installments += 1

    # Last payment date
    last_payment_date = repayments_sorted[0].payment_date if repayments_sorted else None

    # Next due date
    next_due_date = None
    if loan.repayment_type == LoanRepaymentType.DAILY:
        next_due_date = (last_payment_date or loan.start_date) + timedelta(days=1)

    elif loan.repayment_type == LoanRepaymentType.WEEKLY:
        next_due_date = (last_payment_date or loan.start_date)
        while next_due_date.isoweekday() != loan.repayment_day:
            next_due_date += timedelta(days=1)

    elif loan.repayment_type == LoanRepaymentType.MONTHLY:
        month = (last_payment_date or loan.start_date).month
        year = (last_payment_date or loan.start_date).year
        day = min(loan.repayment_day, 28)
        next_due_date = date(year, month, day)
        if next_due_date <= date.today():
            if month == 12:
                next_due_date = date(year + 1, 1, day)
            else:
                next_due_date = date(year, month + 1, day)

    # Repayment list
    repayment_list = [
        {
            "id": r.id,
            "payment_date": r.payment_date,
            "amount_paid": float(r.amount_paid),
            "notes": r.notes
        }
        for r in repayments_sorted
    ]

    return {
        "loan_id": loan.id,
        "lender_name": loan.lender_name,
        "lender_contact": loan.lender_contact,
        "loan_amount": loan.total_amount_payable,
        "total_paid": total_paid,
        "remaining_amount": remaining_amount,
        "remaining_installments": remaining_installments,
        "total_installments": (
            int(float(loan.total_amount_payable) // float(loan.repayment_amount))
            if loan.repayment_amount else None
        ),
        "progress_percent": round((total_paid / float(loan.total_amount_payable)) * 100, 2)
            if loan.total_amount_payable else 0,
        "last_payment_date": last_payment_date,
        "next_due_date": next_due_date,
        "status": loan.status,
        "overdue_days": (
            (date.today() - next_due_date).days
            if next_due_date and next_due_date < date.today() and loan.status != LoanStatus.CLOSED
            else 0
        ),
        "is_fully_paid": remaining_amount <= 0,
        "repayments": repayment_list
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
        # Find the last repayment date
        last_repayment = db.query(LoanRepayment)\
            .filter(LoanRepayment.loan_id == loan.id)\
            .order_by(LoanRepayment.payment_date.desc())\
            .first()
        
        # Daily repayment
        if loan.repayment_type == LoanRepaymentType.DAILY:
            due_date = (last_repayment.payment_date if last_repayment else loan.start_date) + timedelta(days=1)
            if today >= due_date:
                reminders.append(f"Loan '{loan.lender_name}' – Daily repayment of ₹{loan.repayment_amount} is due.")

        # Weekly repayment
        elif loan.repayment_type == LoanRepaymentType.WEEKLY:
            if today.isoweekday() == loan.repayment_day:
                reminders.append(f"Loan '{loan.lender_name}' – Weekly repayment of ₹{loan.repayment_amount} is due today.")

        # Monthly repayment
        elif loan.repayment_type == LoanRepaymentType.MONTHLY:
            if today.day == loan.repayment_day:
                reminders.append(f"Loan '{loan.lender_name}' – Monthly repayment of ₹{loan.repayment_amount} is due today.")

        # Bullet repayment (full at end date)
        elif loan.repayment_type == LoanRepaymentType.BULLET:
            if loan.end_date and today >= loan.end_date - timedelta(days=3):
                reminders.append(f"Loan '{loan.lender_name}' – Full repayment of ₹{loan.total_amount_payable} is due on {loan.end_date}.")

        # Flexible repayment
        elif loan.repayment_type == LoanRepaymentType.FLEXIBLE:
            # Only remind if no payment for last 30 days
            if not last_repayment or (today - last_repayment.payment_date).days >= 30:
                reminders.append(f"Loan '{loan.lender_name}' – Flexible loan: consider making a payment.")

        # No-cost loan
        elif loan.repayment_type == LoanRepaymentType.NO_COST:
            if loan.end_date and today >= loan.end_date - timedelta(days=3):
                reminders.append(f"Loan '{loan.lender_name}' – No-cost loan ends on {loan.end_date}.")

    return reminders

def add_loan_repayment(db:Session,payload:LoanRepaymentRequest):
    loan = db.query(Loan).filter(Loan.id == payload.loan_id).first()
    if not loan:
        raise Exception("loan_not_found")
    loan_repayment = LoanRepayment(
        loan_id=payload.loan_id,
        payment_date=payload.payment_date,
        payment_amount=payload.payment_amount,
        notes=payload.notes
    )
    db.add(loan_repayment)
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

