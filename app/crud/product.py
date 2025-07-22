from slugify import slugify
from sqlalchemy import any_, or_,func,and_, select
from sqlalchemy.orm import Session,joinedload,aliased
from app.helpers.utils import generate_barcode, generate_qr_code
from app.models.business import Business
from app.models.product import Product, ProductCustomField, ProductCustomFieldValue, ProductImage, ProductMasterData
from app.models.user import User
from app.schemas.product import ProductCreate, ProductCustomFieldCreate, ProductCustomFieldUpdate, ProductFilters, ProductMasterDataCreate, ProductMasterDataUpdate
from typing import Tuple, List
import hashlib

def hash_sku(company_key: str, product_id: int) -> str:
    raw = f"{company_key.upper()}_{product_id}"
    hash_str = hashlib.sha1(raw.encode()).hexdigest().upper()
    # Remove non-alphanumeric if needed, take first 12 chars
    return ''.join(filter(str.isalnum, hash_str))[:12]

def create_product(db: Session, product_in: ProductCreate, current_user: User):
    # Generate slug from name["en"] or first available name
    product_name_en = product_in.name.get("en") or next(iter(product_in.name.values()))
    slug = slugify(product_name_en)

    product = Product(
        name=product_in.name,
        slug=slug,
        description=product_in.description or None,
        category_id=product_in.category_id,
        subcategory_path=product_in.subcategory_path if product_in.subcategory_path else None,
        base_unit=product_in.base_unit,
        stock_qty=product_in.stock_qty,
        low_stock_alert=product_in.low_stock_alert,
        purchase_price=product_in.purchase_price,
        selling_price=product_in.selling_price,
        discount_type=product_in.discount_type,
        discount_value=product_in.discount_value,
        max_discount=product_in.max_discount,
        include_tax=product_in.include_tax,
        tax_rate=product_in.tax_rate,
        hsn_code=product_in.hsn_code,
        brand=product_in.brand,
        manufacturer=product_in.manufacturer,
        packed_date=product_in.packed_date,
        expiry_date=product_in.expiry_date,
        is_product_variant=product_in.is_product_variant,
        is_active=product_in.is_active or False,
        is_deleted=False,
        is_online=product_in.is_online or False,
        parent_product_id=product_in.parent_product_id,
        business_id=current_user.business_id,
        created_by_user_id=current_user.id
    )
    db.add(product)
    db.flush()  # To get product.id

    # Generate SKU, barcode, and QR code
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    company_key = business.business_key if business and business.business_key else "UNKNOWN"
    product.sku = hash_sku(company_key, product.id)
    product.barcode = generate_barcode(product.sku)
    product.qr_code = generate_qr_code(product.sku)

    # ➕ Add images (only for non-variant products)
    if product_in.images:
        for img in product_in.images:
            image = ProductImage(
                product_id=product.id,
                media_url=img.media_url,
                media_type=img.media_type,
            )
            db.add(image)

    # ➕ Add custom field values
    for cfv in product_in.custom_field_values or []:
        cf_value = ProductCustomFieldValue(
            product_id=product.id,
            field_id=cfv.field_id,
            value=cfv.value
        )
        db.add(cf_value)

    # ➕ Add variants recursively
    for variant_data in product_in.variants or []:
        variant = create_product(db, variant_data, current_user)  # recursion
        variant.parent_product_id = product.id

    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_in: ProductCreate, current_user: User):
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == current_user.business_id).first()
    if not product:
        raise Exception("Product not found")

    # 🔁 Update product fields (excluding variants, images, custom fields)
    updatable_fields = [
        "name", "description", "category_id", "subcategory_path", "base_unit", "stock_qty",
        "low_stock_alert", "purchase_price", "selling_price", "discount_type", "discount_value",
        "max_discount", "include_tax", "tax_rate", "hsn_code", "brand", "manufacturer",
        "packed_date", "expiry_date", "is_product_variant", "is_active", "is_online", "parent_product_id"
    ]
    for field in updatable_fields:
        if hasattr(product_in, field):
            setattr(product, field, getattr(product_in, field))

    # 🔁 Update subcategory_id from subcategory_path
    product.subcategory_path = product_in.subcategory_path if product_in.subcategory_path else None

    # 🔁 Update images (only for non-variant products)
    if not product.parent_product_id:
        db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
        for img in product_in.images or []:
            image = ProductImage(
                product_id=product.id,
                media_url=img.media_url,
                media_type=img.media_type,
                is_primary=img.media_type == "image" and img.is_primary
            )
            db.add(image)

    # 🔁 Update custom field values
    db.query(ProductCustomFieldValue).filter(ProductCustomFieldValue.product_id == product.id).delete()
    for cfv in product_in.custom_field_values or []:
        cf_value = ProductCustomFieldValue(
            product_id=product.id,
            field_id=cfv.field_id,
            value=cfv.value
        )
        db.add(cf_value)

    # 🔁 Update child variants
    existing_variants = db.query(Product).filter(Product.parent_product_id == product.id).all()
    existing_variant_map = {v.id: v for v in existing_variants}
    received_variant_ids = []

    for variant_data in product_in.variants or []:
        if variant_data.id and variant_data.id in existing_variant_map:
            # 🔁 Update existing variant recursively
            update_product(db, variant_data.id, variant_data, current_user)
            received_variant_ids.append(variant_data.id)
        else:
            # ➕ New variant creation
            new_variant = create_product(db, variant_data, current_user)
            new_variant.parent_product_id = product.id
            received_variant_ids.append(new_variant.id)

    # 🗑️ Delete removed variants
    for variant in existing_variants:
        if variant.id not in received_variant_ids:
            db.query(ProductImage).filter(ProductImage.product_id == variant.id).delete()
            db.query(ProductCustomFieldValue).filter(ProductCustomFieldValue.product_id == variant.id).delete()
            db.delete(variant)

    db.commit()
    db.refresh(product)
    return product

def toggle_product_status(db: Session, status_type:str ,product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()

    if status_type == 'active':
        product.is_active = not product.is_active
    elif status_type == 'online':
        product.is_online = not product.is_online
    db.commit()
    db.refresh(product)
    return product

def get_product_details(db: Session, product_id: int):
    # Get the actual product
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    # If the product has a parent, fetch that instead
    main_product = product.parent if product.parent_product_id else product

    # Eager-load images, custom fields, and variants
    main_product = (
        db.query(Product)
        .options(
            joinedload(Product.images),
            joinedload(Product.custom_field_values),
            joinedload(Product.variants).joinedload(Product.images),
            joinedload(Product.variants).joinedload(Product.custom_field_values)
        )
        .filter(Product.id == main_product.id)
        .first()
    )

    return main_product


def get_product_list(
    db: Session,
    filters:ProductFilters,
    current_user:User
) -> Tuple[int, List[dict]]:
    skip = (filters.page - 1) * filters.page_size

    PrimaryImage = aliased(ProductImage)

    # Base subquery for filtering (search, status, etc.)
    base_filter = db.query(Product.id).filter(
        Product.business_id == current_user.business_id,
        Product.is_deleted == False
    )

    if filters.is_active is not None:
        base_filter = base_filter.filter(Product.is_active == filters.is_active)

    if filters.category_id is not None:
        base_filter = base_filter.filter(Product.category_id == filters.category_id)
    if filters.subcategory_path is not None:
        base_filter = base_filter.filter(
            filters.subcategory_path == any_(Product.subcategory_path)
        )
    if filters.search_text:
        search = f"%{filters.search_text}%"
        base_filter = base_filter.filter(
            or_(
                Product.name['en'].astext.ilike(search),
                Product.description['en'].astext.ilike(search)
            )
        )

    # Collect matching product ids
    matched_ids_subq = base_filter.subquery()

    # Now include those products AND their related variants or parent
    product_ids_to_show = (
        db.query(Product.id)
        .filter(
            or_(
                Product.id.in_(select(matched_ids_subq)),
                Product.parent_product_id.in_(select(matched_ids_subq)),
                Product.id.in_(
                    select(Product.parent_product_id)
                    .where(Product.id.in_(select(matched_ids_subq)))
                    .where(Product.parent_product_id != None)
                )
            )
        )
        .distinct()
        .subquery()
    )

    # Final query for main product list
    query = (
        db.query(Product, PrimaryImage.media_url.label("primary_image"))
        .outerjoin(
            PrimaryImage,
            and_(
                Product.id == PrimaryImage.product_id,
                PrimaryImage.is_primary == True
            )
        )
        .filter(Product.id.in_(select(product_ids_to_show)))
    )

    # Sorting
    sort_field = getattr(Product, filters.sort_by, Product.created_at)
    query = query.order_by(sort_field.desc() if filters.sort_dir == 'desc' else sort_field.asc())

    # Count and paginate
    total = query.count()
    results = query.offset(skip).limit(filters.page_size).all()

    items = []
    for product, primary_image in results:
        items.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "primary_image": primary_image,
            "is_product_variant": product.is_product_variant,
            "parent_product_id": product.parent_product_id
        })

    return total, items

def delete_product(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    product.is_deleted = True
    product.is_active = False  # Optionally deactivate instead of hard delete
    product.is_online = False
    db.commit()
    db.refresh(product)
    return product

#Product Masters methods 
def create_master_data(db: Session, payload: ProductMasterDataCreate,current_user:User):
    data = ProductMasterData(
        business_id = current_user.business_id,
        type=payload.type,
        options=payload.options,
    )
    db.add(data)
    db.commit()
    db.refresh(data)
    return data

def get_master_data_list(db: Session, current_user:User):
    result = db.query(ProductMasterData).filter(ProductMasterData.business_id == current_user.business_id).all()
    return result

def update_master_data(db: Session,payload: ProductMasterDataUpdate):
    data = db.query(ProductMasterData).filter(ProductMasterData.id == payload.id).first()
    data.type = payload.type
    data.options = payload.options
    db.commit()
    db.refresh(data)
    return data


#Product Custom Field APIs
def create_custom_field(db: Session, payload: ProductCustomFieldCreate, current_user: User):
    custom_field = ProductCustomField(
        field_name=payload.field_name,
        field_type=payload.field_type,
        is_required=payload.is_required,
        is_filterable=payload.is_filterable,
        options=payload.options,
        business_id=current_user.business_id,  # scoped to current user's business
    )
    db.add(custom_field)
    db.commit()
    db.refresh(custom_field)
    return custom_field

def get_custom_field_list(db: Session, current_user: User):
    return db.query(ProductCustomField).filter(
        ProductCustomField.business_id == current_user.business_id
    ).order_by(ProductCustomField.created_at.desc()).all()

def update_custom_field(db: Session, payload: ProductCustomFieldUpdate, current_user: User):
    custom_field = db.query(ProductCustomField).filter(
        ProductCustomField.id == payload.id,
        ProductCustomField.business_id == current_user.business_id
    ).first()

    if not custom_field:
        raise Exception("Custom field not found")

    custom_field.field_name = payload.field_name
    custom_field.field_type = payload.field_type
    custom_field.is_required = payload.is_required
    custom_field.is_filterable = payload.is_filterable
    custom_field.options = payload.options

    db.commit()
    db.refresh(custom_field)
    return custom_field

def delete_custom_field(db: Session, custom_field_id: int, current_user: User):
    custom_field = db.query(ProductCustomField).filter(
        ProductCustomField.id == custom_field_id,
        ProductCustomField.business_id == current_user.business_id
    ).first()

    if not custom_field:
        raise Exception("Custom field not found")

    db.delete(custom_field)
    db.commit()
    return custom_field
