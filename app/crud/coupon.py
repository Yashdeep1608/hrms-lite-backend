from typing import Optional

from sqlalchemy import and_
from app.models.coupon import Coupon
from sqlalchemy.orm import Session
from app.schemas.coupon import CreateCoupon, UpdateCoupon

def create_coupon(db: Session, data: CreateCoupon) -> Coupon:
    coupon = Coupon(
        code = data.code,
        type = data.type,
        user_id = data.user_id or None,
        platform_target = data.platform_target,
        business_id = data.business_id or None,
        discount_type = data.discount_type,
        discount_value = data.discount_value,
        usage_limit = data.usage_limit,
        valid_from = data.valid_from,
        valid_to = data.valid_to,
        is_active = data.is_active
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

def get_coupons(db, type: Optional[str] = None,business_id: Optional[int] = None,user_id: Optional[int] = None):
    filters = []
    if type:
        filters.append(Coupon.type == type)
    if business_id:
        filters.append(Coupon.business_id == business_id)
    if user_id:
        filters.append(Coupon.user_id == user_id)
    coupons = db.query(
        Coupon.id,
        Coupon.code,
        Coupon.discount_type,
        Coupon.usage_limit,
        Coupon.is_active,
        Coupon.created_at
        ).filter(and_(*filters) if filters else True).all()
    return coupons

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