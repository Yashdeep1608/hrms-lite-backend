from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session, joinedload,aliased
from app.helpers.utils import apply_operator, parse_date_to_utc_end, parse_date_to_utc_start
from app.models.contact import *
from app.models.enums import RoleTypeEnum
from app.models.user import User
from app.schemas.contact import *
from uuid import UUID, uuid4
from sqlalchemy import or_,and_
from sqlalchemy.exc import SQLAlchemyError # type: ignore

def create_custom_field(db: Session, business_id: int, field: CustomFieldCreate):
    db_field = ContactCustomField(
        id=uuid4(),
        business_id=business_id,
        field_name=field.field_name,
        field_type=field.field_type,
        is_required=field.is_required,
        options=field.options,
    )
    db.add(db_field)
    db.commit()
    db.refresh(db_field)
    return db_field

def get_fields(db: Session, business_id: int):
    return db.query(ContactCustomField).filter_by(business_id=business_id).all()

def update_field(db: Session, field_id: UUID, update_data: CustomFieldUpdate):
    field = db.query(ContactCustomField).filter_by(id=field_id).first()
    if field:
        for key, value in update_data.dict(exclude_unset=True).items():
            setattr(field, key, value)
        db.commit()
        db.refresh(field)
    return field  # ✅ this must return the DB instance, not the request data

def delete_field(db: Session, field_id: UUID):
    field = db.query(ContactCustomField).filter_by(id=field_id).first()
    if field:
        db.delete(field)
        db.commit()
    return field

def create_tag(db: Session, business_id: int, name: str, color: str = None,user_id:Optional[int] = None):
    tag = Tag(business_id=business_id, name=name, color=color,created_by = user_id)
    db.add(tag)
    db.commit()
    db.refresh(tag)
    return tag

def get_tags_for_business(
    db: Session,
    business_id: int,
    search: str = None,
    page: int = 1,
    page_size: int = 20
):
    query = db.query(Tag).filter(Tag.business_id == business_id)

    if search:
        search_term = f"%{search.lower()}%"
        query = query.filter(Tag.name.ilike(search_term))

    total = query.count()
    tags = query.order_by(Tag.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": tags,
        "total": total,
        "page": page,
        "page_size": page_size
    }

def update_tag(db: Session, tag_id: UUID, name: str = None, color: str = None):
    tag = db.query(Tag).filter_by(id=tag_id).first()
    if not tag:
        return None
    if name: tag.name = name
    if color: tag.color = color
    db.commit()
    db.refresh(tag)
    return tag

def delete_tag(db: Session, tag_id: UUID):
    tag = db.query(Tag).filter_by(id=tag_id).first()
    if tag:
        db.delete(tag)
        db.commit()
    return tag

def create_group(db: Session, business_id: int, data: GroupCreate, created_by: int):
    group = Groups(
        business_id=business_id,
        name=data.name,
        description=data.description,
        is_dynamic=data.is_dynamic,
        filters=data.filters,
        created_by=created_by
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

def get_groups(db: Session, business_id: int, search: Optional[str], page: int, page_size: int):
    query = db.query(Groups).filter(Groups.business_id == business_id).with_entities(Groups.id,Groups.name,Groups.description,Groups.is_dynamic)
    if search:
        query = query.filter(Groups.name.ilike(f"%{search}%"))

    total = query.count()
    groups = query.order_by(Groups.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    return {"items": groups, "total": total, "page": page, "page_size": page_size}

def update_group(db: Session, group_id: UUID, update_data: GroupUpdate):
    group = db.query(Groups).filter_by(id=group_id).first()
    if not group:
        return None

    for key, value in update_data.dict(exclude_unset=True).items():
        setattr(group, key, value)

    db.commit()
    db.refresh(group)
    return group

def delete_group(db: Session, group_id: UUID):
    group = db.query(Groups).filter_by(id=group_id).first()
    if group:
        db.delete(group)
        db.commit()
    return group

def get_group_data(db:Session,group_id: UUID):
    group = db.query(Groups).filter_by(id = group_id).first()
    return group

def create_contact(db: Session, user_id: int, business_id: int, contact_data: ContactCreate):
    try:
        # 1. Check for existing contact
        existing_contact = db.query(Contact).filter_by(
            phone_number=contact_data.phone_number,
            isd_code=contact_data.isd_code,
            country_code=contact_data.country_code
        ).first()

        if existing_contact:
            # Update basic fields if needed
            updated = False
            if contact_data.email and contact_data.email != existing_contact.email:
                existing_contact.email = contact_data.email
                updated = True
            if contact_data.gender and contact_data.gender != existing_contact.gender:
                existing_contact.gender = contact_data.gender
                updated = True
            if contact_data.preferred_language and contact_data.preferred_language != existing_contact.preferred_language:
                existing_contact.preferred_language = contact_data.preferred_language
                updated = True
            if updated:
                db.commit()
                db.refresh(existing_contact)

            contact = existing_contact
        else:
            # Create new contact
            contact = Contact(
                phone_number=contact_data.phone_number,
                email=contact_data.email,
                isd_code=contact_data.isd_code,
                country_code=contact_data.country_code,
                gender=contact_data.gender,
                preferred_language=contact_data.preferred_language
            )
            db.add(contact)
            db.commit()
            db.refresh(contact)

        # 2. Check if BusinessContact already exists
        existing_business_contact = db.query(BusinessContact).filter_by(
            business_id=business_id,
            contact_id=contact.id
        ).first()

        if existing_business_contact:
            raise ValueError("Contact already present")

        # 3. Create new BusinessContact
        business_contact = BusinessContact(
            business_id=business_id,
            contact_id=contact.id,
            first_name=contact_data.first_name,
            last_name=contact_data.last_name,
            label=contact_data.label,
            notes=contact_data.notes,
            is_favorite=contact_data.is_favorite,
            managed_by_user_id=user_id,
            sponsor_id=contact_data.sponsor_id
        )
        db.add(business_contact)
        db.commit()
        db.refresh(business_contact)

        # 4. Add custom fields if any
        if contact_data.custom_fields:
            for cf in contact_data.custom_fields:
                value = ContactCustomValue(
                    business_contact_id=business_contact.id,
                    field_id=cf.field_id,
                    value=cf.value
                )
                db.add(value)
            db.commit()

        return business_contact

    except SQLAlchemyError as e:
        db.rollback()
        raise e

def delete_business_contact(db: Session, business_contact_id: str):
    bc = db.query(BusinessContact).filter_by(id=business_contact_id).first()
    if bc:
        db.delete(bc)
        db.commit()
        return True
    return False

def get_contact_by_business_contact_id(db: Session, business_contact_id: UUID):
    return (
        db.query(BusinessContact)
        .options(
            # Load the custom_values relationship, and then load the 'field' relationship on ContactCustomValue
            joinedload(BusinessContact.custom_values)
            .joinedload(ContactCustomValue.field),  # Correctly reference the field relationship
            joinedload(BusinessContact.contact)  # Load base contact info as well
        )
        .filter_by(id=business_contact_id)
        .first()
    )

def get_contacts_for_dropdown(db: Session,user:dict ,business_id: int, search: str = "", page: int = 1, page_size: int = 30):
    query = db.query(
        BusinessContact.id.label("business_contact_id"),
        Contact.id.label("contact_id"),
        BusinessContact.first_name,
        BusinessContact.last_name,
        Contact.email,
        Contact.phone_number
    ).join(BusinessContact.contact).filter(
        BusinessContact.business_id == business_id
    )


    role = user.role
    user_id = user.id

    if role == RoleTypeEnum.EMPLOYEE:
        # Employee sees only their contacts
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    elif role == RoleTypeEnum.ADMIN:
        # Admin sees all contacts of the business
        pass

    # Optional: If needed, restrict unknown roles (fallback)
    else:
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    if search:
        query = query.filter(
            or_(
                BusinessContact.first_name.ilike(f"%{search}%"),
                BusinessContact.last_name.ilike(f"%{search}%"),
                BusinessContact.label.ilike(f"%{search}%"),
                Contact.email.ilike(f"%{search}%"),
                Contact.phone_number.ilike(f"%{search}%"),
            )
        )

    results = query.offset((page -1) * page_size).limit(page_size).all()

    # Convert to list of dicts
    return [
        {
            "business_contact_id": r.business_contact_id,
            "contact_id": r.contact_id,
            "first_name": r.first_name,
            "last_name": r.last_name,
            "email": r.email,
            "phone_number": r.phone_number
        }
        for r in results
    ]

def update_business_contact(db: Session, business_contact_id: str, update_data: ContactUpdate):
    try:
        bc = db.query(BusinessContact).filter_by(id=business_contact_id).first()
        if not bc:
            return None

        # 1. Update BusinessContact fields
        bc_fields = {"first_name", "last_name", "label", "notes", "is_favorite", "sponsor_id"}
        for field, value in update_data.dict(exclude_unset=True).items():
            if field in bc_fields:
                setattr(bc, field, value)

        # 2. Update Contact fields (only some)
        contact = bc.contact
        contact_fields = {
            "email": update_data.email,
            "gender": update_data.gender,
            "preferred_language": update_data.preferred_language
        }
        for field, value in contact_fields.items():
            if value is not None:
                setattr(contact, field, value)

        # 3. Update custom fields (delete existing & insert new if provided)
        if update_data.custom_fields is not None:
            # Delete existing values
            db.query(ContactCustomValue).filter_by(business_contact_id=bc.id).delete()

            # Add new values
            for cf in update_data.custom_fields:
                new_value = ContactCustomValue(
                    business_contact_id=bc.id,
                    field_id=cf.field_id,
                    value=cf.value
                )
                db.add(new_value)

        db.commit()
        db.refresh(bc)
        return bc

    except SQLAlchemyError as e:
        db.rollback()
        raise e  # or raise HTTPException(status_code=500, detail="Update failed")
    
def get_all_contacts(
    db: Session,
    user: dict,
    business_id: int,
    page_number: int = 1,
    page_size: int = 20,
    sort_by: str = "created_at",
    sort_dir: str = "desc",
    search: str = "",
    group_id:UUID = '',
    filters: Optional[Dict[str, Any]] = None,
    last_seen: Optional[Any] = None
):
    query = db.query(
        BusinessContact.id.label("business_contact_id"),
        Contact.id.label("contact_id"),
        BusinessContact.first_name,
        BusinessContact.last_name,
        BusinessContact.label,
        BusinessContact.is_favorite,
        BusinessContact.sponsor_id,
        BusinessContact.created_at,
        Contact.email,
        Contact.phone_number
    ).join(BusinessContact.contact).filter(
        BusinessContact.business_id == business_id
    )


    role = user.role
    user_id = user.id

    if role == RoleTypeEnum.EMPLOYEE:
        # Employee sees only their contacts
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    elif role == RoleTypeEnum.ADMIN:
        # Admin sees all contacts of the business
        pass

    # Optional: If needed, restrict unknown roles (fallback)
    else:
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    if group_id:
        group = db.query(Groups).filter(Groups.id == group_id).first()
        if group:
            if group.is_dynamic:
                filters = group.filters.copy()
            else:
                query = query.join(GroupContact).filter(GroupContact.group_id == group_id)

    # 1. Tag filtering
    tag_ids = filters.get("tags", []) if filters else []
    if tag_ids:
        query = query.join(BusinessContactTag).filter(BusinessContactTag.tag_id.in_(tag_ids))

    # 2. Standard contact fields
    contacts_filters = filters.get("contacts", {}) if filters else {}
    for key, value in contacts_filters.items():
        if value is not None and value != "":
            if hasattr(Contact, key):
                query = query.filter(getattr(Contact, key) == value)
        # else: Optionally, log or handle unknown fields

    # 3. Business contact fields (date range, is_favorite, etc.)
    business_contacts_filters = filters.get("business_contacts", {}) if filters else {}
    start_date = parse_date_to_utc_start(business_contacts_filters.get("start_date"))
    end_date = parse_date_to_utc_end(business_contacts_filters.get("end_date"))
    is_favorite = business_contacts_filters.get("is_favorite")
    if start_date:
        query = query.filter(BusinessContact.created_at >= start_date)
    if end_date:
        query = query.filter(BusinessContact.created_at < end_date)
    if is_favorite is not None and is_favorite != "":
        is_fav_bool = str(is_favorite).strip().lower() == "true"
        query = query.filter(BusinessContact.is_favorite == is_fav_bool)

    # 4. Custom field filters
    custom_fields_filters = filters.get("custom_fields", {}) if filters else {}
    for field_id, filter_info in custom_fields_filters.items():
        value = filter_info.get("value")
        operator = filter_info.get("operator", "equal")
        field_type = filter_info.get("type")

        # Determine whether to skip based on type
        skip = False

        if field_type in ["text", "dropdown", "date"]:
            skip = value is None or value == ""
        elif field_type == "boolean":
            # Boolean False is valid, only skip if None
            skip = value is None
        elif isinstance(value, list):
            skip = len(value) == 0

        if skip:
            continue

        # Aliased join for filtering
        alias = aliased(ContactCustomValue)
        query = query.join(
            alias,
            and_(
                alias.business_contact_id == BusinessContact.id,
                alias.field_id == field_id
            )
        )
        query = query.filter(apply_operator(alias.value, operator, value, field_type))

    # 5. Search (on name or other fields)
    if search:
        query = query.filter(
            or_(
                BusinessContact.first_name.ilike(f"%{search}%"),
                BusinessContact.last_name.ilike(f"%{search}%"),
                BusinessContact.label.ilike(f"%{search}%"),
                Contact.email.ilike(search),
                Contact.phone_number.ilike(search),
            )
        )

    # 6. Keyset pagination
    if last_seen:
        sort_column = getattr(BusinessContact, sort_by)
        query = query.filter(sort_column < last_seen)

    # 7. Sorting
    if sort_by in ["first_name", "last_name","label","created_at"]:
        sort_column = getattr(BusinessContact, sort_by)
    else:
        sort_column = getattr(Contact, sort_by)
    if sort_dir == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # 8. Pagination
    contacts = query.offset((page_number - 1) * page_size).limit(page_size).all()

    results = [
    {
            "business_contact_id": row.business_contact_id,
            "contact_id": row.contact_id,
            "first_name": row.first_name,
            "last_name": row.last_name,
            "email": row.email,
            "phone_number": row.phone_number,
            "label":row.label,
            "is_favorite":row.is_favorite,
            "sponsor_id":row.sponsor_id,
            "created_at":row.created_at,
        }
        for row in contacts
    ]
    return results

def get_all_contacts_count(
    db: Session,
    user: dict,
    business_id: int,
    search: str = "",
    group_id:UUID = '',
    filters: Optional[Dict[str, Any]] = None,
):
    query = db.query(
        BusinessContact.id.label("business_contact_id"),
    ).join(BusinessContact.contact).filter(
        BusinessContact.business_id == business_id
    )


    role = user.role
    user_id = user.id

    if role == RoleTypeEnum.EMPLOYEE:
        # Employee sees only their contacts
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    elif role == RoleTypeEnum.ADMIN:
        # Admin sees all contacts of the business
        pass

    # Optional: If needed, restrict unknown roles (fallback)
    else:
        query = query.filter(BusinessContact.managed_by_user_id == user_id)

    if group_id:
        group = db.query(Groups).filter(Groups.id == group_id).first()
        if group:
            if group.is_dynamic:
                filters = group.filters.copy()
            else:
                query = query.join(GroupContact).filter(GroupContact.group_id == group_id)

    # 1. Tag filtering
    tag_ids = filters.get("tags", []) if filters else []
    if tag_ids:
        query = query.join(BusinessContactTag).filter(BusinessContactTag.tag_id.in_(tag_ids))

    # 2. Standard contact fields
    contacts_filters = filters.get("contacts", {}) if filters else {}
    for key, value in contacts_filters.items():
        if value is not None and value != "":
            if hasattr(Contact, key):
                query = query.filter(getattr(Contact, key) == value)
        # else: Optionally, log or handle unknown fields

    # 3. Business contact fields (date range, is_favorite, etc.)
    business_contacts_filters = filters.get("business_contacts", {}) if filters else {}
    start_date = parse_date_to_utc_start(business_contacts_filters.get("start_date"))
    end_date = parse_date_to_utc_end(business_contacts_filters.get("end_date"))
    is_favorite = business_contacts_filters.get("is_favorite")
    if start_date:
        query = query.filter(BusinessContact.created_at >= start_date)
    if end_date:
        query = query.filter(BusinessContact.created_at < end_date)
    if is_favorite is not None and is_favorite != "":
        is_fav_bool = str(is_favorite).strip().lower() == "true"
        query = query.filter(BusinessContact.is_favorite == is_fav_bool)

    # 4. Custom field filters
    custom_fields_filters = filters.get("custom_fields", {}) if filters else {}
    for field_id, filter_info in custom_fields_filters.items():
        value = filter_info.get("value")
        operator = filter_info.get("operator", "equal")
        field_type = filter_info.get("type")

        # Determine whether to skip based on type
        skip = False

        if field_type in ["text", "dropdown", "date"]:
            skip = value is None or value == ""
        elif field_type == "boolean":
            # Boolean False is valid, only skip if None
            skip = value is None
        elif isinstance(value, list):
            skip = len(value) == 0

        if skip:
            continue

        # Aliased join for filtering
        alias = aliased(ContactCustomValue)
        query = query.join(
            alias,
            and_(
                alias.business_contact_id == BusinessContact.id,
                alias.field_id == field_id
            )
        )
        query = query.filter(apply_operator(alias.value, operator, value, field_type))

    # 5. Search (on name or other fields)
    if search:
        query = query.filter(
            or_(
                BusinessContact.first_name.ilike(f"%{search}%"),
                BusinessContact.last_name.ilike(f"%{search}%"),
                BusinessContact.label.ilike(f"%{search}%"),
                Contact.email.ilike(search),
                Contact.phone_number.ilike(search),
            )
        )

    # 6. Total
    total = query.count()
    return total

def assign_contacts_to_groups(db, contact_ids, group_ids, assigned_by):
    # Fetch all existing (contact_id, group_id) pairs to avoid duplicates
    existing = db.query(GroupContact.business_contact_id, GroupContact.group_id).filter(
        GroupContact.business_contact_id.in_(contact_ids),
        GroupContact.group_id.in_(group_ids)
    ).all()
    existing_set = set(existing)

    new_links = []

    for contact_id in contact_ids:
        for group_id in group_ids:
            if (contact_id, group_id) not in existing_set:
                new_links.append(
                    GroupContact(
                        business_contact_id=contact_id,
                        group_id=group_id,
                        assigned_by=assigned_by,
                    )
                )

    if new_links:
        db.bulk_save_objects(new_links)
        db.commit()

def assign_contacts_to_tags(db, contact_ids, tag_ids, assigned_by):
    # Fetch all existing (contact_id, tag_id) pairs to avoid duplicates
    existing = db.query(BusinessContactTag.business_contact_id, BusinessContactTag.tag_id).filter(
        BusinessContactTag.business_contact_id.in_(contact_ids),
        BusinessContactTag.tag_id.in_(tag_ids)
    ).all()
    existing_set = set(existing)

    new_links = []

    for contact_id in contact_ids:
        for tag_id in tag_ids:
            if (contact_id, tag_id) not in existing_set:
                new_links.append(
                    BusinessContactTag(
                        business_contact_id=contact_id,
                        tag_id=tag_id,
                        assigned_by=assigned_by,
                    )
                )

    if new_links:
        db.bulk_save_objects(new_links)
        db.commit()

def get_contact_groups(db:Session,contact_id:UUID):
    groups = (
        db.query(Groups)
        .join(GroupContact, Groups.id == GroupContact.group_id)
        .filter(GroupContact.business_contact_id == contact_id)
        .all()
    )
    return [
        {
            "id": str(group.id),
            "name": group.name,
            # Add other group fields as needed
        }
        for group in groups
    ]

def get_contact_tags(db:Session,contact_id:UUID):
    tags = (
        db.query(Tag)
        .join(BusinessContactTag, Tag.id == BusinessContactTag.tag_id)
        .filter(BusinessContactTag.business_contact_id == contact_id)
        .all()
    )
    return [
        {
            "id": str(tag.id),
            "name": tag.name,
            # Add other tag fields as needed
        }
        for tag in tags
    ]

def get_group_dropdown(db:Session,current_user:User):
    query = db.query(Groups.id,Groups.name).filter(Groups.business_id == current_user.business_id)
    groups = query.order_by(Groups.name.asc()).all()
    return [{"id": o.id, "name": o.name} for o in groups]

def get_tag_dropdown(db:Session,current_user:User):
    query = db.query(Tag.id,Tag.name).filter(Tag.business_id == current_user.business_id)
    tags = query.order_by(Tag.name.asc()).all()
    return [{"id": o.id, "name": o.name} for o in tags]

def get_ledgers(db:Session, search:str, contact_id:UUID, type:str, page:int, page_size:int, current_user:User):
    # Base query
    query = (
        db.query(
            BusinessContactLedger,
            BusinessContact.id.label("contact_id"),
            BusinessContact.first_name,
            BusinessContact.last_name,
            BusinessContact.label,
            BusinessContact.notes,
            BusinessContact.city,
            BusinessContact.state,
            BusinessContact.country,
            BusinessContact.postal_code,
        )
        .join(BusinessContact, BusinessContactLedger.business_contact_id == BusinessContact.id)
        .filter(BusinessContactLedger.business_id == current_user.business_id)
    )

    # Optional filters
    if contact_id:
        query = query.filter(BusinessContactLedger.business_contact_id == contact_id)
    if type:
        query = query.filter(BusinessContactLedger.entry_type == type)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (BusinessContact.first_name.ilike(search_term)) |
            (BusinessContact.last_name.ilike(search_term)) |
            (BusinessContact.label.ilike(search_term)) |
            (BusinessContactLedger.notes.ilike(search_term))
        )

    # Sorting: latest first
    query = query.order_by(BusinessContactLedger.created_at.desc())

    # Pagination
    total = query.count()
    ledgers = query.offset((page - 1) * page_size).limit(page_size).all()

    # Convert to dict
    results = []
    for ledger, contact_id, first_name, last_name, label, notes, city, state, country, postal_code in ledgers:
        results.append({
            "id": ledger.id,
            "business_id": ledger.business_id,
            "business_contact_id": ledger.business_contact_id,
            "entry_type": ledger.entry_type,
            "amount": float(ledger.amount),
            "payment_method": ledger.payment_method,
            "notes": ledger.notes,
            "created_at": ledger.created_at,
            "contact": {
                "id": contact_id,
                "first_name": first_name,
                "last_name": last_name,
                "label": label,
                "notes": notes,
                "city": city,
                "state": state,
                "country": country,
                "postal_code": postal_code
            }
        })

    return {
        "total": total,
        "items": results
    }

def create_ledger(db: Session, data: CreateLedger, current_user:User):
    group = BusinessContactLedger(
        business_id=current_user.business_id,
        business_contact_id=data.business_contact_id,
        entry_type=data.entry_type,
        amount=data.amount,
        payment_method=data.payment_method or None,
        notes=data.notes
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group
