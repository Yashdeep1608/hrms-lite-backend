
from calendar import monthrange
from datetime import timedelta
from requests import Session
from sqlalchemy import and_, case, desc, func
from app.models.contact import BusinessContact, BusinessContactLedger
from app.models.enums import CartOrderStatus, OrderPaymentMethod, RoleTypeEnum
from app.models.expense import Expense, ExpenseCategory
from app.models.loan import Loan, LoanRepayment, LoanRepaymentStatus, LoanRepaymentType, LoanStatus
from app.models.order import Order
from app.models.supplier import Supplier, SupplierPurchase, SupplierTransaction
from app.models.user import User
from app.models.product import *
from dateutil.relativedelta import relativedelta  # for month calculations


def get_dashboard_products_stats(db: Session, current_user: User, duration_type: int = 1):
    """
    Returns inventory dashboard metrics for the current user's business.

    duration_type:
        1 = Current Month
        2 = Current Week
        3 = Today
        4 = Last Month
        5 = Last 3 Months
        6 = Last 6 Months
    Role-based:
        - EMPLOYEE: low_stock_products only
        - ADMIN: full inventory metrics + top-selling products
    """
    business_id = current_user.business_id
    now = datetime.now(timezone.utc)

    # Determine the start and end date based on duration_type
    if duration_type == 1:  # Current Month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 2:  # Current Week (week starts Monday)
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 3:  # Today
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 4:  # Last Month
        first_day_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = first_day_current_month - relativedelta(months=1)
        start_date = start_date.replace(day=1)
        end_date = first_day_current_month - timedelta(seconds=1)
    elif duration_type == 5:  # Last 3 Months
        start_date = now - relativedelta(months=3)
    elif duration_type == 6:  # Last 6 Months
        start_date = now - relativedelta(months=6)
    else:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    filter_start = start_date
    filter_end = now
    if duration_type == 4:  # Last Month
        filter_end = end_date

    response = {}

    # =====================
    # Employee View
    # =====================
    if current_user.role == RoleTypeEnum.EMPLOYEE:
        # Aggregate stock per product
        product_agg = (
            db.query(
                Product.id,
                Product.name,
                Product.low_stock_alert,
                func.coalesce(func.sum(ProductBatch.quantity), 0).label("total_stock")
            )
            .join(Product.batches)
            .filter(Product.business_id == business_id)
            .group_by(Product.id)
            .all()
        )

        # Separate low stock and out-of-stock products
        low_stock_products = [
            {"id": p.id, "name": p.name, "stock": p.total_stock, "low_stock_alert": p.low_stock_alert}
            for p in product_agg
            if 0 < p.total_stock <= p.low_stock_alert
        ]

        out_of_stock_products = [
            {"id": p.id, "name": p.name, "stock": p.total_stock}
            for p in product_agg
            if p.total_stock == 0
        ]

        response["low_stock_products"] = len(low_stock_products) or 0
        response["out_of_stock_products"] = len(out_of_stock_products) or 0

    # =====================
    # Admin View
    # =====================
    elif current_user.role == RoleTypeEnum.ADMIN:
        # Aggregate stock and inventory value per product
        product_agg = (
            db.query(
                Product.id,
                Product.name,
                Product.low_stock_alert,
                func.coalesce(func.sum(ProductBatch.quantity), 0).label("total_stock"),
                func.coalesce(func.sum(ProductBatch.quantity * ProductBatch.purchase_price), 0).label("inventory_value")
            )
            .join(Product.batches)
            .filter(Product.business_id == business_id)
            .group_by(Product.id)
            .all()
        )

        total_stock = sum(p.total_stock for p in product_agg)
        inventory_value = sum(p.inventory_value for p in product_agg)

        low_stock_products = [p for p in product_agg if p.total_stock <= p.low_stock_alert and p.total_stock > 0]
        out_of_stock_products = [p for p in product_agg if p.total_stock <= 0]

        # Top selling products in the selected duration
        top_selling_products_query = db.query(
            Product.id,
            Product.name,
            func.coalesce(func.sum(ProductStockLog.quantity), 0).label("sold_qty")
        ).join(Product.stock_logs).filter(
            Product.business_id == business_id,
            ProductStockLog.source == ProductStockSource.ORDER,
            ProductStockLog.created_at >= filter_start,
            ProductStockLog.created_at <= filter_end
        ).group_by(Product.id).order_by(desc('sold_qty')).limit(3)

        top_selling_products = top_selling_products_query.all()

        response.update({
            "total_stock": total_stock,
            "inventory_value": float(inventory_value),
            "low_stock_products": len(low_stock_products) or 0,
            "out_of_stock_products": len(out_of_stock_products) or 0,
            "top_selling_products": [
                {"id": p.id, "name": p.name, "sold_qty": p.sold_qty}
                for p in top_selling_products
            ]
        })

    return response

def get_dashboard_order_stats(db: Session, current_user: User, duration_type: int = 1):
    """
    Returns order metrics for dashboard
    Employee: pending/new orders only
    Admin: full metrics including revenue, avg order value, cancellations
    """

    business_id = current_user.business_id
    now = datetime.now(timezone.utc)

    # Determine start/end based on duration_type
    if duration_type == 1:  # Current Month
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 2:  # Current Week
        start_date = now - timedelta(days=now.weekday())
        start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 3:  # Today
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif duration_type == 4:  # Last Month
        first_day_current_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        start_date = first_day_current_month - relativedelta(months=1)
        start_date = start_date.replace(day=1)
        end_date = first_day_current_month - timedelta(seconds=1)
    elif duration_type == 5:  # Last 3 Months
        start_date = now - relativedelta(months=3)
    elif duration_type == 6:  # Last 6 Months
        start_date = now - relativedelta(months=6)
    else:
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    filter_start = start_date
    filter_end = now if duration_type != 4 else end_date

    # Employee View: only pending orders
    if current_user.role == RoleTypeEnum.EMPLOYEE:
        pending_orders_count = db.query(Order).filter(
            Order.business_id == business_id,
            Order.status == 'pending',
            Order.created_at >= filter_start,
            Order.created_at <= filter_end
        ).count()

        return {
            "pending_orders": pending_orders_count
        }

    # Admin View: full stats
    total_orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).count()

    pending_orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.order_status == CartOrderStatus.PENDING,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).count()

    completed_orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.order_status == CartOrderStatus.COMPLETED,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).count()

    cancelled_orders = db.query(Order).filter(
        Order.business_id == business_id,
        Order.order_status == CartOrderStatus.CANCELLED,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).count()

    revenue = db.query(func.coalesce(func.sum(Order.total_amount), 0)).filter(
        Order.business_id == business_id,
        Order.order_status == CartOrderStatus.COMPLETED,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).scalar()

    avg_order_value = db.query(func.coalesce(func.avg(Order.total_amount), 0)).filter(
        Order.business_id == business_id,
        Order.order_status == CartOrderStatus.COMPLETED,
        Order.created_at >= filter_start,
        Order.created_at <= filter_end
    ).scalar()

    return {
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "revenue": float(revenue),
        "avg_order_value": float(avg_order_value)
    }

def get_sales_graph_data(
    db: Session,
    current_user,
    is_weekly: bool = True,
    is_monthly: bool = False,
    is_daily: bool = False
):
    """
    Returns sales graph data for weekly, monthly, or daily.
    - Weekly: Monday to Sunday of current week (labels fixed Mon-Sun).
    - Monthly: Last 6 months including current month (labels fixed).
    - Daily: Current month day-wise (1 to end of month, labels fixed).
    """

    business_id = current_user.business_id
    now = datetime.now(timezone.utc)

    results = []

    # ---------------- WEEKLY GRAPH ----------------
    if is_weekly:
        # Get start (Monday) and end (Sunday) of current week
        start_of_week = now - timedelta(days=now.weekday())
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)

        # Query sales grouped by day
        sales_data = db.query(
            func.date_trunc('day', Order.created_at).label('period'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).filter(
            Order.business_id == business_id,
            Order.order_status == CartOrderStatus.COMPLETED,
            Order.created_at >= start_of_week,
            Order.created_at <= end_of_week
        ).group_by('period').all()

        sales_map = {s.period.date(): float(s.revenue) for s in sales_data}

        # Labels fixed Mon–Sun
        labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i in range(7):
            day = start_of_week.date() + timedelta(days=i)
            results.append({"label": labels[i], "value": sales_map.get(day, 0)})

    # ---------------- MONTHLY GRAPH ----------------
    elif is_monthly:
        # Last 6 months including current
        months = []
        for i in range(5, -1, -1):  # 6 months back
            m = (now - relativedelta(months=i)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            months.append(m)

        start_date = months[0]
        end_date = (months[-1] + relativedelta(months=1)) - timedelta(seconds=1)

        # Query sales grouped by month
        sales_data = db.query(
            func.date_trunc('month', Order.created_at).label('period'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).filter(
            Order.business_id == business_id,
            Order.order_status == CartOrderStatus.COMPLETED,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by('period').all()

        sales_map = {s.period.strftime("%Y-%m"): float(s.revenue) for s in sales_data}

        # Build labels always 6 months
        for m in months:
            key = m.strftime("%Y-%m")
            label = m.strftime("%b %y").upper()  # MAR 25
            results.append({"label": label, "value": sales_map.get(key, 0)})

    # ---------------- DAILY GRAPH ----------------
    elif is_daily:
        # Current month start and end
        start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        last_day = monthrange(now.year, now.month)[1]
        end_date = start_date.replace(day=last_day, hour=23, minute=59, second=59)

        # Query sales grouped by day
        sales_data = db.query(
            func.date_trunc('day', Order.created_at).label('period'),
            func.coalesce(func.sum(Order.total_amount), 0).label('revenue')
        ).filter(
            Order.business_id == business_id,
            Order.order_status == CartOrderStatus.COMPLETED,
            Order.created_at >= start_date,
            Order.created_at <= end_date
        ).group_by('period').all()

        sales_map = {s.period.day: float(s.revenue) for s in sales_data}

        # Labels 1 → last_day
        for d in range(1, last_day + 1):
            results.append({"label": str(d), "value": sales_map.get(d, 0)})

    return results

def get_expense_summary(db: Session, business_id: int):
    today = datetime.now(timezone.utc).date()
    start_current_month = today.replace(day=1)
    start_last_month = (start_current_month - timedelta(days=1)).replace(day=1)
    end_last_month = start_current_month - timedelta(days=1)
    end_current_month = (start_current_month + relativedelta(months=1)) - timedelta(days=1)

    # --- Query 1: totals for current & last month ---
    totals = db.query(
        func.coalesce(func.sum(
            case((Expense.expense_date >= start_current_month, Expense.amount), else_=0)
        ), 0).label("current_month_total"),
        func.coalesce(func.sum(
            case((and_(Expense.expense_date >= start_last_month, Expense.expense_date <= end_last_month), Expense.amount), else_=0)
        ), 0).label("last_month_total")
    ).filter(Expense.business_id == business_id).first()

    # --- Query 2: breakdown by category for current month ---
    breakdown = (
        db.query(
            ExpenseCategory.id,
            ExpenseCategory.name,
            func.coalesce(func.sum(Expense.amount), 0).label("total")
        )
        .join(ExpenseCategory, Expense.category_id == ExpenseCategory.id)
        .filter(
            Expense.business_id == business_id,
            Expense.expense_date >= start_current_month,
            Expense.expense_date <= end_current_month,
            ExpenseCategory.parent_id.is_(None)  # only top-level categories
        )
        .group_by(ExpenseCategory.id, ExpenseCategory.name)
        .all()
    )

    return {
        "current_month_total": float(totals.current_month_total or 0),
        "last_month_total": float(totals.last_month_total or 0),
        "breakdown": [
            {"id": cat_id, "name": name, "total": float(total)} 
            for cat_id, name, total in breakdown
        ]
    }

def get_loans_stats(db: Session, business_id: int):
    today = datetime.now(timezone.utc).date()

    # Loan-level stats
    loan_stats = db.query(
        func.count(case((Loan.status == LoanStatus.ACTIVE, 1))).label("active_loans"),
        func.coalesce(func.sum(Loan.total_amount_payable), 0).label("total_disbursed"),
        func.count(case((
            and_(Loan.status == LoanStatus.ACTIVE, Loan.end_date < today), 1
        ))).label("overdue_loans")
    ).filter(Loan.business_id == business_id).first()

    # Repayment-level stats
    repayment_stats = db.query(
        func.count(case((
            and_(
                LoanRepayment.status == LoanRepaymentStatus.PENDING,
                LoanRepayment.payment_date >= today
            ), 1
        ))).label("due_repayments"),
        func.count(case((LoanRepayment.status == LoanRepaymentStatus.OVERDUE, 1))).label("overdue_repayments")
    ).join(Loan).filter(Loan.business_id == business_id).first()

    return {
        "active": loan_stats.active_loans,
        "due": repayment_stats.due_repayments,
        "disbursed": float(loan_stats.total_disbursed or 0),
        "overdue": repayment_stats.overdue_repayments + loan_stats.overdue_loans
    }

def get_supplier_stats(db: Session, business_id: int):
    try:
        # Purchases stats (all suppliers of business)
        purchase_stats = db.query(
            func.count(SupplierPurchase.id).label("total_purchases"),
            func.coalesce(func.sum(SupplierPurchase.total_amount), 0).label("total_purchase_amount"),
        ).join(Supplier).filter(Supplier.business_id == business_id).first()

        # Transaction stats (all suppliers of business)
        transaction_stats = db.query(
           func.coalesce(
                func.sum(
                    case(
                        (SupplierTransaction.payment_method != OrderPaymentMethod.CREDIT, SupplierTransaction.amount),
                        else_=0
                    )
                ),
                0
            ).label("total_paid_amount"),
        ).join(Supplier).filter(Supplier.business_id == business_id).first()

        # Safe values
        total_purchase_amount = float(getattr(purchase_stats, "total_purchase_amount", 0) or 0)
        total_paid_amount = float(getattr(transaction_stats, "total_paid_amount", 0) or 0)
        total_credit_amount = total_purchase_amount - total_paid_amount
        credit_percentage = (total_credit_amount / total_purchase_amount * 100) if total_purchase_amount else 0

        return {
            "total_suppliers": db.query(Supplier).filter(Supplier.business_id == business_id).count(),
            "total_purchases": getattr(purchase_stats, "total_purchases", 0) or 0,
            "total_purchase_amount": round(total_purchase_amount, 2),
            "total_paid_amount": round(total_paid_amount, 2),
            "total_credit_amount": round(total_credit_amount, 2),
            "credit_percentage": round(credit_percentage, 2),
        }
    except Exception as e:
        raise Exception(str(e))
    
def get_ledger_stats(db: Session, business_id: int):
    try:
        # Aggregate debit & credit
        totals = db.query(
            func.coalesce(func.sum(
                case((BusinessContactLedger.entry_type == "debit", BusinessContactLedger.amount), else_=0)
            ), 0).label("total_debit"),
            func.coalesce(func.sum(
                case((BusinessContactLedger.entry_type == "credit", BusinessContactLedger.amount), else_=0)
            ), 0).label("total_credit"),
        ).filter(BusinessContactLedger.business_id == business_id).first()

        total_debit = float(totals.total_debit or 0)
        total_credit = float(totals.total_credit or 0)
        final_balance = total_debit - total_credit  # positive => others owe you, negative => you owe

        # Top 3 contacts by balance
        top_contacts = (
            db.query(
                BusinessContact.id,
                BusinessContact.first_name,
                BusinessContact.last_name,
                (
                    func.coalesce(func.sum(
                        case((BusinessContactLedger.entry_type == "debit", BusinessContactLedger.amount), else_=0)
                    ), 0)
                    -
                    func.coalesce(func.sum(
                        case((BusinessContactLedger.entry_type == "credit", BusinessContactLedger.amount), else_=0)
                    ), 0)
                ).label("balance")
            )
            .join(BusinessContact.ledgers)
            .filter(BusinessContact.business_id == business_id)
            .group_by(BusinessContact.id, BusinessContact.first_name)
            .order_by(desc("balance"))   # biggest outstanding first
            .limit(3)
            .all()
        )

        return {
            "total_debit": round(total_debit, 2),
            "total_credit": round(total_credit, 2),
            "final_balance": round(final_balance, 2),
            "top_contacts": [
                {
                    "id": c.id,
                    "name": (
                        (c.first_name or "").strip() + " " + (c.last_name or "").strip()
                    ).strip() or f"Contact-{str(c.id)[:8]}",  # fallback if both empty
                    "balance": float(c.balance or 0)
                }
                for c in top_contacts
            ]
        }

    except Exception as e:
        raise Exception(str(e))
    
def get_loan_repayment_reminders(db: Session, current_user: User):
    today = datetime.now(timezone.utc).date()
    reminders = []

    loans = db.query(Loan).filter(
        Loan.business_id == current_user.business_id,
        Loan.status == LoanStatus.ACTIVE
    ).all()

    for loan in loans:
        repayments = db.query(LoanRepayment).filter(
            LoanRepayment.loan_id == loan.id,
            LoanRepayment.status != LoanRepaymentStatus.PAID
        ).order_by(LoanRepayment.payment_date.asc()).all()

        # --- Generate structured reminders ---
        for r in repayments:
            if r.payment_date == today:
                reminders.append({
                    "loan_id": str(loan.id),
                    "type": "due_today",
                    "amount": float(loan.repayment_amount or 0),
                    "date": str(r.payment_date)
                })
            elif r.payment_date < today:
                reminders.append({
                    "loan_id": str(loan.id),
                    "type": "overdue",
                    "amount": float(loan.repayment_amount or 0),
                    "date": str(r.payment_date)
                })

        # Bullet repayment
        if loan.repayment_type == LoanRepaymentType.BULLET and loan.end_date and today >= loan.end_date - timedelta(days=3):
            reminders.append({
                "loan_id": str(loan.id),
                "type": "bullet_due",
                "amount": float(loan.total_amount_payable or 0),
                "date": str(loan.end_date)
            })

        # Flexible repayment
        if loan.repayment_type == LoanRepaymentType.FLEXIBLE:
            last_paid = db.query(LoanRepayment).filter(
                LoanRepayment.loan_id == loan.id,
                LoanRepayment.status == LoanRepaymentStatus.PAID
            ).order_by(LoanRepayment.payment_date.desc()).first()

            if not last_paid or (today - last_paid.payment_date).days >= 30:
                reminders.append({
                    "loan_id": str(loan.id),
                    "type": "flexible_reminder",
                    "amount": None,  # no fixed amount
                    "date": str(today)
                })

        # No-cost loan ending
        if loan.repayment_type == LoanRepaymentType.NO_COST and loan.end_date and today >= loan.end_date - timedelta(days=3):
            reminders.append({
                "loan_id": str(loan.id),
                "type": "no_cost_ending",
                "amount": None,  # just an ending notice
                "date": str(loan.end_date)
            })

    return reminders