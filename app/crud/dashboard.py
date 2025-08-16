
from calendar import monthrange
from datetime import timedelta
from requests import Session
from sqlalchemy import desc, func
from app.models.enums import CartOrderStatus, RoleTypeEnum
from app.models.order import Order
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
