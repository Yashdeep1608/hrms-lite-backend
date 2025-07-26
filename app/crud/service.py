from typing import List, Tuple
from sqlalchemy.orm import Session,joinedload
from sqlalchemy import or_,and_
from sqlalchemy.orm import Session,joinedload,aliased
from app.models.service import Service, ServiceMedia, ServiceSchedule
from app.schemas.service import ServiceCreate, ServiceUpdate

def create_service(db: Session, service_in: ServiceCreate):
    service = Service(
        name = service_in.name,
        business_id=service_in.business_id,
        category_id=service_in.category_id,
        subcategory_id=service_in.subcategory_id,
        description=service_in.description,
        price=service_in.price,
        discount_type=service_in.discount_type,
        discount_value=service_in.discount_value,
        include_tax=service_in.include_tax,
        tax_value=service_in.tax_value,
        additional_fees=service_in.additional_fees,
        location_type=service_in.location_type,
        capacity=service_in.capacity,
        booking_required=service_in.booking_required,
        custom_fields=service_in.custom_fields,
        tags=service_in.tags,
        duration_minutes=service_in.duration_minutes,
        cancellation_policy=service_in.cancellation_policy,
        is_featured=service_in.is_featured,
        is_active= True,  # Default to active
        is_deleted=False  # Default to not deleted
    )
    db.add(service)
    db.flush()  # To get service.id
    schedule = ServiceSchedule(
            service_id=service.id,
            schedule_type=service_in.schedules.schedule_type,
            days_of_week=service_in.schedules.days_of_week,
            start_time=service_in.schedules.start_time,
            end_time=service_in.schedules.end_time,
            duration_days=service_in.schedules.duration_days,
            duration_nights=service_in.schedules.duration_nights,
            start_date=service_in.schedules.start_date,
            end_date=service_in.schedules.end_date,
            buffer_time_before=service_in.schedules.buffer_time_before,
            buffer_time_after=service_in.schedules.buffer_time_after,
            lead_time=service_in.schedules.lead_time,
            recurring=service_in.schedules.recurring
        )
    db.add(schedule)
        
    
    media = ServiceMedia(
        service_id=service.id,
        media_url=service_in.medias.media_url,
        media_type=service_in.medias.media_type,
        is_primary=service_in.medias.is_primary
    )
    db.add(media)
    db.flush()
    

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

    # Update schedule if provided
    if service_in.schedules:
        if service.schedules:
            for field, value in service_in.schedules.model_dump(exclude_unset=True).items():
                setattr(service.schedules, field, value)
        else:
            new_schedule = ServiceSchedule(
                service_id=service.id,
                **service_in.schedules.model_dump()
            )
            db.add(new_schedule)

    # Update media if provided
    if service_in.medias:
        if service.medias:
            for field, value in service_in.medias.model_dump(exclude_unset=True).items():
                setattr(service.medias, field, value)
        else:
            new_media = ServiceMedia(
                service_id=service.id,
                **service_in.medias.model_dump()
            )
            db.add(new_media)

    db.commit()
    db.refresh(service)
    return service


def toggle_service_status(db: Session, service_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()
    service.is_active = not service.is_active
    db.commit()
    db.refresh(service)
    return service

from sqlalchemy.orm import joinedload

def get_service_details(db: Session, service_id: int):
    service = (
        db.query(Service)
        .options(
            joinedload(Service.schedules),
            joinedload(Service.medias)
        )
        .filter(Service.id == service_id)
        .first()
    )
    return service


def get_service_list(
    db: Session,
    business_id: int,
    page: int = 1,
    page_size: int = 20,
    search_text: str = '',
    is_active: bool = None,
    sort_by: str = 'created_at',
    sort_dir: str = 'desc',
    category_id: int = None,
    subcategory_id: int = None,
) -> Tuple[int, List[dict]]:
    skip = (page - 1) * page_size

    # Aliased image for primary image join
    ServiceImage = aliased(ServiceMedia)

    # Base query with outer join to fetch only the primary image
    query = (
        db.query(Service, ServiceImage.media_url.label("service_image"))
        .outerjoin(
            ServiceImage,
            and_(
                Service.id == ServiceImage.service_id,
                ServiceImage.is_primary == True
            )
        )
        .filter(Service.business_id == business_id)
    )
    query = query.filter(Service.is_deleted == False)  # Exclude soft-deleted services
    # Search filter on localized name/description
    if search_text:
        search = f"%{search_text}%"
        query = query.filter(
            or_(
                Service.name.astext.ilike(search),
                Service.description.astext.ilike(search)
            )
        )

    # Filter by active status
    if is_active is not None:
        query = query.filter(Service.is_active == is_active)

    # Filter by category/subcategory
    if category_id is not None:
        query = query.filter(Service.category_id == category_id)
    if subcategory_id is not None:
        query = query.filter(Service.subcategory_id == subcategory_id)
    # Sorting
    sort_field = getattr(Service, sort_by, Service.created_at)
    if sort_dir == 'desc':
        sort_field = sort_field.desc()
    else:
        sort_field = sort_field.asc()

    query = query.order_by(sort_field)

    # Total count
    total = query.count()

    # Pagination
    results = query.offset(skip).limit(page_size).all()

    # Prepare response list
    items = []
    for service, service_image in results:
        items.append({
            "id": service.id,
            "name": service.name,
            "is_active": service.is_active,
            "created_at": service.created_at,
            "price": service.price,
            "discount_type": service.discount_type,
            "discount_value": service.discount_value,
            "service_image": service_image
        })

    return total, items

def delete_service(db: Session, service_id: int):
    service = db.query(Service).filter(Service.id == service_id).first()
    service.is_active = False
    service.is_deleted = True  # Soft delete
    db.commit()
    db.refresh(service)
    return service

