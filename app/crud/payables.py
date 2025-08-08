from datetime import timedelta
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
    # Aggregate purchases
    purchase_stats = db.query(
        func.count(SupplierPurchase.id).label("total_purchases"),
        func.coalesce(func.sum(SupplierPurchase.total_amount), 0).label("total_purchase_amount"),
        func.max(SupplierPurchase.purchase_date).label("last_purchase_date"),
        func.avg(SupplierPurchase.total_amount).label("avg_purchase_value"),
        func.max(SupplierPurchase.total_amount).label("largest_purchase")
    ).filter(SupplierPurchase.supplier_id == supplier_id).first()

    # Aggregate transactions
    transaction_stats = db.query(
        func.count(SupplierTransaction.id).label("total_transactions"),
        func.coalesce(func.sum(SupplierTransaction.amount), 0).label("total_paid_amount")
    ).filter(SupplierTransaction.supplier_id == supplier_id).first()

    total_credit_amount = float(purchase_stats.total_purchase_amount) - float(transaction_stats.total_paid_amount)
    credit_percentage = (total_credit_amount / float(purchase_stats.total_purchase_amount) * 100) \
        if purchase_stats.total_purchase_amount else 0

    return {
        "supplier_id": supplier_id,
        "total_purchases": purchase_stats.total_purchases or 0,
        "total_purchase_amount": float(purchase_stats.total_purchase_amount or 0),
        "total_paid_amount": float(transaction_stats.total_paid_amount or 0),
        "total_credit_amount": round(total_credit_amount, 2),
        "credit_percentage": round(credit_percentage, 2),
        "total_transactions": transaction_stats.total_transactions or 0,
        "last_purchase_date": purchase_stats.last_purchase_date,
        "avg_purchase_value": round(float(purchase_stats.avg_purchase_value or 0), 2),
        "largest_purchase": round(float(purchase_stats.largest_purchase or 0), 2)
    }

def get_supplier_purchases(db: Session, filters:SupplierPurchaseFilters):
    query = db.query(SupplierPurchase)
    
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