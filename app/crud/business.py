from sqlalchemy import asc, desc, or_
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
import re

from app.models import Business, BusinessCategory
from app.models.category import Category
from app.models.user import User
from app.schemas.business import BusinessCreate, BusinessUpdate, CategoryCreateUpdate


# Get Business by ID
def get_business_by_id(db: Session, business_id: int):
    return db.query(Business).filter(
        Business.id == business_id,
         Business.is_deleted == False,
         Business.is_active == True
    ).first()

# Get Business by UserId
def get_business_by_user_id(db: Session, user_id: int):
    return db.query(Business).filter(
        Business.user_id == user_id,
         Business.is_deleted == False,
         Business.is_active == True
    ).first()

# Get Business by Business Key
def get_business_by_key(db: Session, business_key: str):
    return db.query(Business).filter(
        Business.business_key == business_key,
         Business.is_deleted == False,
         Business.is_active == True
    ).first()

# Create Business
def create_business(db: Session, data: BusinessCreate) -> Business:
    unique_key = generate_unique_business_key(db, data.business_name)

    new_business = Business(
        business_name=data.business_name,
        business_key = unique_key,
        legal_name=data.legal_name,
        business_type=data.business_type,
        business_category=data.business_category,
        registration_number=data.registration_number,
        gst_number=data.gst_number,
        pan_number=data.pan_number,
        address_line1=data.address_line1,
        address_line2=data.address_line2,
        city=data.city,
        state=data.state,
        country=data.country,
        postal_code=data.postal_code,
        isd_code=data.isd_code,
        phone_number=data.phone_number,
        email=data.email,
        website=data.website,
        is_active=True,
        is_deleted=False,
    )
    db.add(new_business)
    db.commit()
    db.refresh(new_business)
    return new_business
# Update Business
def update_business(db: Session, business:Business, data: BusinessUpdate):
    try:
        data_dict = data.model_dump(exclude_unset=True)

        for field, value in data_dict.items():
            if hasattr(business, field):
                setattr(business, field, value)

        business.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(business)
        return business

    except Exception as e:
        db.rollback()
        raise
# Deactivate Business
def deactivate_business(db: Session, business: Business) -> bool:
    business = db.query(Business).filter(
        Business.id == business.id,
        Business.is_deleted == False
    ).first()

    if not business:
        return False

    business.is_deleted = True
    business.is_active = False
    db.commit()
    return True

# Business key generation
def generate_unique_business_key(db: Session, name: str) -> str:
    base_key = re.sub(r'[^a-zA-Z0-9]', '', name).lower()
    key = base_key
    suffix = 1

    # Check and increment suffix until a unique key is found
    while db.query(Business).filter(Business.business_key == key).first():
        key = f"{base_key}{suffix}"
        suffix += 1
        if suffix > 100:
            raise Exception("Too many businesses with the same name. Try a more specific name.")

    return key

# Get Business Categories
def get_business_categories(db: Session) -> List[BusinessCategory]:
    return db.query(BusinessCategory).all()

# Create User Business Categories
def create_category(db: Session, category_data: CategoryCreateUpdate) -> Category:
    new_category = Category(
        name=category_data.name,
        parent_id=category_data.parent_id,
        business_id=category_data.business_id,
        is_active=True,
        category_image=category_data.category_image,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category

def get_categories_by_business(
    db: Session,
    business_id: int,
    search_text: Optional[str] = '',
    is_active: Optional[bool] = None,
    parent_id: Optional[int] = None,
    sort_by: str = 'created_at',
    sort_dir: str = 'desc',
    skip: int = 0,
    limit: int = 50
):
    query = db.query(Category).filter(Category.business_id == business_id)

    # Filter: search by name
    if search_text:
        query = query.filter(Category.name.ilike(f"%{search_text}%"))

    # Filter: is_active (True/False)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    # Filter: parent_id for nested categories
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)

    total = query.count()

    # Sorting
    sort_column_map = {
        "name": Category.name,
        "created_at": Category.created_at,
        "parent_id": Category.parent_id,
        "is_active": Category.is_active,
    }
    sort_column = sort_column_map.get(sort_by, Category.created_at)
    sort_method = asc if sort_dir == 'asc' else desc
    query = query.order_by(sort_method(sort_column)).offset(skip).limit(limit)
    items = query.all()

    # Get all top-level categories (used for parent category dropdown)
    if parent_id is not None:
        parent_categories = (
        db.query(Category)
        .filter(Category.business_id == business_id)
        .filter(
            or_(
                Category.id == parent_id,
                Category.parent_id == parent_id
            )
        )
        .order_by(Category.name.asc())
        .all()
    )
    else:
        parent_categories = (
            db.query(Category)
            .filter(Category.business_id == business_id)
            .filter(Category.parent_id.is_(None))
            .order_by(Category.name.asc())
            .all()
        )

    return {
        "items": items,
        "total": total,
        "parent_categories": parent_categories,
    }

def get_category_by_id(db: Session, category_id: int) -> Optional[Category]:
    return db.query(Category).filter(Category.id == category_id).first()

def update_category(db: Session, category: Category, update_data: CategoryCreateUpdate) -> Category:
    data_dict = update_data.model_dump(exclude_unset=True)
    for field, value in data_dict.items():
        if hasattr(category, field):
            setattr(category, field, value)
    category.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(category)
    return category

def toggle_category(db: Session, category: Category):
    category.is_active = not category.is_active
    category.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(category)
    return category

def get_categories_for_dropdown(
    db: Session,
    current_user:User
) -> List[Category]:
    # Step 1: Fetch all categories
    categories = (
        db.query(Category)
        .filter(
            Category.business_id == current_user.business_id,
            Category.is_active == True
        )
        .order_by(Category.name.asc())
        .all()
    )

    # Step 2: Index categories by ID
    category_dict = {
        cat.id: {
            "id": cat.id,
            "name": cat.name,
            "parent_id": cat.parent_id,
            "children": []
        }
        for cat in categories
    }

    # Step 3: Build the nested tree
    root_categories = []
    for cat in category_dict.values():
        if cat["parent_id"]:
            parent = category_dict.get(cat["parent_id"])
            if parent:
                parent["children"].append(cat)
        else:
            root_categories.append(cat)
    
    return root_categories