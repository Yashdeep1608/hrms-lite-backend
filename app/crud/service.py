from typing import List, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from app.models.service import Service
from app.models.user import User
from app.schemas.service import ServiceCreate, ServiceFilter, ServiceUpdate

def create_service(db: Session, service_data: ServiceCreate, current_user:User):
    service = Service(
        name=service_data.name,
        description=service_data.description,
        cancellation_policy=service_data.cancellation_policy,
        image_url=service_data.image_url,

        business_id=current_user.business_id,
        created_by_user_id=current_user.id,

        parent_service_id=service_data.parent_service_id,
        category_id=service_data.category_id,
        subcategory_path=service_data.subcategory_path,

        price=service_data.price,
        discount_type=service_data.discount_type,
        discount_value=service_data.discount_value,
        max_discount = service_data.max_discount,
        include_tax=service_data.include_tax,
        tax_rate=service_data.tax_rate,

        location_type=service_data.location_type,
        capacity=service_data.capacity,
        booking_required=service_data.booking_required,

        duration_minutes=service_data.duration_minutes,
        schedule_type=service_data.schedule_type,

        days_of_week=service_data.days_of_week,
        start_time=service_data.start_time,
        end_time=service_data.end_time,

        duration_days=service_data.duration_days,
        duration_weeks=service_data.duration_weeks,
        duration_months=service_data.duration_months,

        start_date=service_data.start_date,
        end_date=service_data.end_date,

        buffer_time_before=service_data.buffer_time_before,
        buffer_time_after=service_data.buffer_time_after,
        lead_time=service_data.lead_time,

        recurring=service_data.recurring,

        tags=service_data.tags,
        is_featured=service_data.is_featured,
        is_online=service_data.is_online,
        is_active=True,
        is_deleted=False,
    )
    db.add(service)
    db.commit()
    db.refresh(service)
    return service

def update_service(db: Session, service_in: ServiceUpdate):
    service = db.query(Service).filter(Service.id == service_in.id).first()
    if not service:
        raise Exception("service_not_found")

    # Update scalar fields only
    for field, value in service_in.model_dump(exclude_unset=True).items():
        if field not in ("schedules", "medias") and hasattr(service, field):
            setattr(service, field, value)
    db.commit()
    db.refresh(service)
    return service

def get_service_details(db: Session, service_id: int):
    service = (
        db.query(Service)
        .filter(Service.id == service_id)
        .first()
    )
    return service

def get_service_list(
    db: Session,
    filters: ServiceFilter,
    current_user:User
) -> Tuple[int, List[dict]]:
    skip = (filters.page - 1) * filters.page_size

    query = db.query(Service).filter(Service.business_id == current_user.business_id)
    query = query.filter(Service.is_deleted == False)

    # Search
    if filters.search_text:
        search = f"%{filters.search_text}%"
        query = query.filter(
            or_(
                Service.name.ilike(search),
                Service.description.ilike(search)
            )
        )
    # Active filter
    if filters.is_active is not None:
        query = query.filter(Service.is_active == filters.is_active)
    # Online filter
    if filters.is_online is not None:
        query = query.filter(Service.is_online == filters.is_online)
    # Featured filter
    if filters.is_active is not None:
        query = query.filter(Service.is_featured == filters.is_featured)

    # Category/Subcategory filter
    if filters.category_id is not None:
        query = query.filter(filters.category_id == func.any(Service.subcategory_path))

    # Sort
    sort_field = getattr(Service, filters.sort_by, Service.created_at)
    if filters.sort_dir == 'desc':
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()

    query = query.order_by(sort_field)

    total = query.count()
    results = query.offset(skip).limit(filters.page_size).all()

    items = []
    for service in results:
        base_price = service.price or 0
        discount = 0

        if service.discount_type == 'percentage' and service.discount_value:
            discount = (base_price * service.discount_value) / 100
            if discount > service.max_discount:
                discount = service.max_discount
        elif service.discount_type == 'flat' and service.discount_value:
            discount = service.discount_value

        discounted_price = base_price - discount

        if not service.include_tax and service.tax_rate:
            tax = (discounted_price * service.tax_rate) / 100
            final_price = discounted_price + tax
        else:
            final_price = discounted_price

        if final_price < 0:
            final_price = 0
        items.append({
            "id": service.id,
            "name": service.name,
            "image_url":service.image_url,
            "is_active": service.is_active,
            "is_online": service.is_online,
            "is_featured": service.is_featured,
            "created_at": service.created_at,
            "final_price": round(final_price, 2)
        })

    return total, items

def delete_service(db: Session, service_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()
    service.is_active = False
    service.is_deleted = True  # Soft delete
    db.commit()
    db.refresh(service)
    return service

def get_service_dropdown(db:Session,is_parent:bool,search:str,current_user:User):
    query = db.query(Service).filter(Service.business_id == current_user.business_id)

    if search:
        search = search.lower()
        query = query.filter(
            or_(
                Service.name.ilike(search),
                Service.description.ilike(search)
            )
        )
    if is_parent:
        query = query.filter(Service.parent_service_id.is_(None))
        
    services = query.order_by(Service.name.asc()).all()

    items = []
    for service in services:
        base_price = service.price or 0
        discount = 0

        if service.discount_type == 'percentage' and service.discount_value:
            discount = (base_price * service.discount_value) / 100
            if discount > service.max_discount:
                discount = service.max_discount
        elif service.discount_type == 'flat' and service.discount_value:
            discount = service.discount_value

        discounted_price = base_price - discount

        if not service.include_tax and service.tax_rate:
            tax = (discounted_price * service.tax_rate) / 100
            final_price = discounted_price + tax
        else:
            final_price = discounted_price

        items.append({
            "id": service.id,
            "name": service.name,
            "final_price": round(final_price, 2)
        })

    return items
