from sqlalchemy import asc, desc, or_
from datetime import datetime, timezone
from typing import Optional, List

from sqlalchemy.orm import Session
import re

from app.models import Business, BusinessCategory
from app.models.category import Category
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
    sort_dir: str = 'desc'
) -> List[Category]:
    query = db.query(Category).filter(Category.business_id == business_id)

    # Filter: search by name (assumes multilingual structure like { "en": "Shoes" })
    if search_text:
        query = query.filter(Category.name['en'].astext.ilike(f"%{search_text}%"))

    # Filter: is_active (True/False)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)

    # Filter: parent_id (e.g., show subcategories only)
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    else:
        query = query.filter(Category.parent_id.is_(None))  # Show only top-level categories if no parent_id is provided

    # Sorting logic
    sort_column_map = {
        "name": Category.name['en'].astext,
        "created_at": Category.created_at,
        "parent_id": Category.parent_id,
        "is_active": Category.is_active,
        # Add more if needed
    }

    sort_column = sort_column_map.get(sort_by, Category.created_at)
    sort_method = asc if sort_dir == 'asc' else desc
    query = query.order_by(sort_method(sort_column))

    return query.all()

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

def get_categories_for_dropdown(db: Session, business_id: int) -> List[Category]:
    return (
        db.query(Category)
        .filter(Category.business_id == business_id,Category.parent_id.is_(None), Category.is_active == True)
        .with_entities(Category.id, Category.name)
        .all()
    )
def get_subcategories_for_dropdown(db: Session, business_id: int) -> List[Category]:
    return (
        db.query(Category)
        .filter(Category.business_id == business_id,Category.parent_id > 0 ,Category.is_active == True)
        .with_entities(Category.id, Category.name,Category.parent_id)
        .all()
    )
