from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import and_, or_
from app.helpers.utils import parse_date_to_utc_end, parse_date_to_utc_start
from app.models.coupon import Coupon
from sqlalchemy.orm import Session
from app.models.enums import RoleTypeEnum
from app.models.user import User
from app.schemas.coupon import CouponFilters, CreateCoupon, UpdateCoupon

def get_coupon_dropdown(db:Session,current_user:User):
    query = db.query(Coupon).filter(Coupon.business_id == current_user.business_id)
    coupons = query.order_by(Coupon.created_at.asc()).all()
    return coupons

def create_coupon(db: Session, data: CreateCoupon, current_user: User) -> Coupon:
    coupon = Coupon(
        code=data.code,
        type=data.type,

        # Required fields
        label=data.label,
        description=data.description,
        terms_condition=data.terms_condition,
        discount_type=data.discount_type,
        discount_value=data.discount_value,

        # Limits & logic
        usage_limit=data.usage_limit,
        available_limit=data.available_limit,
        max_discount_amount=data.max_discount_amount,
        min_cart_value=data.min_cart_value or 0,
        is_auto_applied=data.is_auto_applied,
        is_active=data.is_active,

        # Date
        valid_from = datetime.combine(data.valid_from, datetime.min.time()).replace(tzinfo=timezone.utc),
        valid_to = datetime.combine(data.valid_to + timedelta(days=1), datetime.min.time()).replace(tzinfo=timezone.utc),


        # Platform fields
        user_id=data.user_id,
        platform_target=data.platform_target,

        # Business
        business_id=current_user.business_id,

        # Audit
        created_by_user_id =current_user.id,

        # JSONB exclusions
        exclude_product_ids=data.exclude_product_ids or [],
        exclude_service_ids=data.exclude_service_ids or [],
    )

    db.add(coupon)
    db.commit()
    db.refresh(coupon)
    return coupon

def update_coupon(db: Session, coupon_id: int, data: UpdateCoupon) -> Coupon:
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    
    if not coupon:
        raise Exception("coupon_not_found")
    
    data_dict = data.model_dump(exclude_unset=True)

    for field, value in data_dict.items():
            if hasattr(coupon, field):
                setattr(coupon, field, value)

    db.commit()
    db.refresh(coupon)
    return coupon

def get_coupons(db: Session, filters: CouponFilters,current_user:User) -> List[dict]:
    query = db.query(
        Coupon.id,
        Coupon.code,
        Coupon.label,
        Coupon.type,
        Coupon.discount_type,
        Coupon.discount_value,
        Coupon.available_limit,
        Coupon.is_active,
        Coupon.user_id,
        Coupon.created_at,
    )

    # Filtering
    conditions = []
    conditions.append(Coupon.business_id == current_user.business_id)
    if filters.discount_type:
        conditions.append(Coupon.discount_type == filters.discount_type)

    if filters.is_active is not None:
        conditions.append(Coupon.is_active == filters.is_active)

    if filters.user_id:
        conditions.append(Coupon.user_id == filters.user_id)
       
    if filters.from_date:
        conditions.append(Coupon.created_at >= filters.from_date)

    if filters.to_date:
        conditions.append(Coupon.created_at <= filters.to_date)

    if filters.search:
        conditions.append(or_(
            Coupon.code.ilike(f"%{filters.search}%"),
            Coupon.label.ilike(f"%{filters.search}%")
        ))

    if conditions:
        query = query.filter(and_(*conditions))

    # Sorting
    sort_field = getattr(Coupon, filters.sort_by, Coupon.created_at)
    if filters.sort_dir == 'desc':
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()

    query = query.order_by(sort_field)

    total = query.count()

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    query = query.offset(offset).limit(filters.page_size)

    results = query.all()
    return {
        'total': total,
        'items': [dict(row._mapping) for row in results]
    }
    
def get_coupon_details(db, coupon_id: int):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    if not coupon:
        raise Exception("coupon_not_found")
    return coupon

def delete_coupon(db: Session, coupon_id: int):
    coupon = db.query(Coupon).filter(Coupon.id == coupon_id).first()
    db.delete(coupon)
    db.commit()
    return True