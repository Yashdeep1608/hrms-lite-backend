from slugify import slugify
from sqlalchemy import any_, or_,func,and_, select
from sqlalchemy.orm import Session,joinedload,aliased
from app.helpers.utils import generate_barcode, generate_qr_code
from app.models.business import Business
from app.models.product import Product, ProductCustomField, ProductCustomFieldValue, ProductImage, ProductMasterData
from app.models.user import User
from app.schemas.product import ProductCreate, ProductCustomFieldCreate, ProductCustomFieldUpdate, ProductFilters, ProductMasterDataCreate, ProductMasterDataUpdate, ProductUpdate
from typing import Tuple, List
import hashlib
from sqlalchemy.orm import subqueryload

def hash_sku(company_key: str, product_id: int) -> str:
    raw = f"{company_key.upper()}_{product_id}"
    hash_str = hashlib.sha1(raw.encode()).hexdigest().upper()
    # Remove non-alphanumeric if needed, take first 12 chars
    return ''.join(filter(str.isalnum, hash_str))[:12]

def generate_unique_slug(db: Session, name: str, business_id: int) -> str:
    base_slug = slugify(name)  # "second"
    slug = base_slug
    index = 1
    while db.query(Product).filter(Product.slug == slug, Product.business_id == business_id).first():
        slug = f"{base_slug}-{index}"
        index += 1
    return slug

def create_product(db: Session, product_in: ProductCreate, current_user: User):
    parent_product = None

    # If this is a variant, fetch parent and inherit fields if not set
    if product_in.parent_product_id:
        parent_product = db.query(Product).filter(Product.id == product_in.parent_product_id).first()

    def inherit(field_name, fallback=None):
        return getattr(product_in, field_name, None) or (getattr(parent_product, field_name) if parent_product else fallback)

    # Generate slug from name["en"] or first available name
    product_name_en = product_in.name.get("en") or next(iter(product_in.name.values()))
    slug = generate_unique_slug(db, product_name_en, current_user.business_id)

    product = Product(
        name=product_in.name,
        slug=slug,
        description=product_in.description or None,
        category_id=inherit("category_id"),
        subcategory_path=inherit("subcategory_path"),
        base_unit=inherit("base_unit"),
        package_type=inherit("package_type"),
        stock_qty=product_in.stock_qty,
        low_stock_alert=product_in.low_stock_alert,
        purchase_price=product_in.purchase_price,
        selling_price=product_in.selling_price,
        discount_type=product_in.discount_type,
        discount_value=product_in.discount_value,
        max_discount=product_in.max_discount,
        include_tax=inherit("include_tax", False),
        tax_rate=inherit("tax_rate", 0.0),
        hsn_code=inherit("hsn_code"),
        image_url=inherit("image_url"),
        brand=inherit("brand"),
        manufacturer=inherit("manufacturer"),
        packed_date=product_in.packed_date,
        expiry_date=product_in.expiry_date,
        is_product_variant=product_in.is_product_variant,
        is_active=product_in.is_active or False,
        is_deleted=False,
        is_online=product_in.is_online or False,
        parent_product_id=product_in.parent_product_id,
        business_id=current_user.business_id,
        tags=product_in.tags,
        created_by_user_id=current_user.id
    )

    db.add(product)
    db.flush()  # Get product.id for SKU generation

    # Generate SKU, barcode, QR
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    company_key = business.business_key if business and business.business_key else "UNKNOWN"
    product.sku = hash_sku(company_key, product.id)
    product.barcode = generate_barcode(product.sku)
    product.qr_code = generate_qr_code(product.sku)

    # Only add images if not a variant
    if product_in.images and not product_in.parent_product_id:
        for img in product_in.images:
            image = ProductImage(
                product_id=product.id,
                media_url=img.media_url,
                media_type=img.media_type,
            )
            db.add(image)

    # Add custom field values
    for cfv in product_in.custom_field_values or []:
        cf_value = ProductCustomFieldValue(
            product_id=product.id,
            field_id=cfv.field_id,
            value=str(cfv.value) or None
        )
        db.add(cf_value)

    # Recursively create variants
    for variant_data in product_in.variants or []:
        variant_data.parent_product_id = product.id
        variant_data.is_product_variant = True
        create_product(db, variant_data, current_user)

    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, product_in: ProductUpdate, current_user: User):
    product = db.query(Product).filter(Product.id == product_id, Product.business_id == current_user.business_id).first()
    if not product:
        raise Exception("Product not found")

    # 🔁 Update product fields (excluding variants, images, custom fields)
    updatable_fields = [
        "name", "description", "category_id", "subcategory_path", "base_unit", "stock_qty",
        "low_stock_alert", "purchase_price", "selling_price", "discount_type", "discount_value",
        "max_discount", "include_tax", "tax_rate", "hsn_code", "brand", "manufacturer",
        "packed_date", "expiry_date", "is_product_variant", "is_active", "is_online", "parent_product_id","tags"
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

    # 🔁 Update child variants only if this is a variant-enabled product
    received_variant_ids = []

    if product.is_product_variant:
        existing_variants = db.query(Product).filter(Product.parent_product_id == product.id).all()
        existing_variant_map = {v.id: v for v in existing_variants}

        for variant_data in product_in.variants or []:
            variant_dict = variant_data.model_dump()  # Converts to dict
            variant_update = ProductUpdate(**variant_dict)  # Cast to ProductUpdate with id

            if variant_update.id and variant_update.id in existing_variant_map:
                variant_update.is_product_variant = True
                update_product(db, variant_update.id, variant_update, current_user)
                received_variant_ids.append(variant_update.id)
            else:
                variant_update.parent_product_id = product.id
                variant_update.is_product_variant = True
                new_variant = create_product(db, variant_update, current_user)
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
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None

    # Step 1: Classify product type
    is_variant = product.is_product_variant and product.parent_product_id is not None
    is_linked = not product.is_product_variant and product.parent_product_id is not None
    is_base = not product.parent_product_id  # Any top-level product

    # Step 2: Determine main product to return
    main_product_id = product.parent_product_id if is_variant else product.id

    # Step 3: Build load options
    load_options = [
        subqueryload(Product.images),
        subqueryload(Product.custom_field_values),
    ]

    # ✅ Only load variants if base and explicitly marked as variantable
    should_load_variants = (
        not product.parent_product_id and product.is_product_variant
    )

    if should_load_variants:
        load_options.extend([
            subqueryload(Product.variants).joinedload(Product.custom_field_values),
        ])

    main_product = (
        db.query(Product)
        .options(*load_options)
        .filter(Product.id == main_product_id)
        .first()
    )

    # Step 4: Always return empty variants list if no variants loaded
    if should_load_variants:
        if not main_product.variants:
            main_product.variants = []
    else:
        main_product.variants = []  # Ensure clean for UI

    # Step 5: Attach linked_products (lightweight)
    linked_products = []

    if is_linked:
        # Current product is a child (e.g. 27), get parent and siblings
        parent = db.query(Product).filter(Product.id == product.parent_product_id).first()
        if parent:
            # Add parent first
            linked_products.append(parent)

            # Add siblings (excluding the current product)
            siblings = (
                db.query(Product)
                .filter(
                    Product.parent_product_id == product.parent_product_id,
                    Product.id != product.id,
                    Product.is_product_variant == False  # or True if variant children expected
                )
                .all()
            )
            linked_products.extend(siblings)

    elif is_base and not product.is_product_variant:
        # Current product is a base non-variant (e.g. 26), get all children
        children = (
            db.query(Product)
            .filter(
                Product.parent_product_id == product.id,
                Product.is_product_variant == False
            )
            .all()
        )
        linked_products = [p for p in children]

    main_product.linked_products = linked_products

    return main_product



def get_product_list(
    db: Session,
    filters: ProductFilters,
    current_user: User,
    lang: str
) -> Tuple[int, List[dict]]:
    skip = (filters.page - 1) * filters.page_size

    query = db.query(Product).filter(
    Product.business_id == current_user.business_id,
    Product.is_deleted == False,
    or_(
            and_(Product.parent_product_id.is_(None), Product.is_product_variant == False),
            and_(Product.parent_product_id.is_not(None), Product.is_product_variant == False),
            and_(Product.parent_product_id.is_(None), Product.is_product_variant == True),
        )
    )
    if filters.is_active is not None:
        query = query.filter(Product.is_active == filters.is_active)

    if filters.category_id is not None:
        query = query.filter(
            or_(
                Product.category_id == filters.category_id,
                Product.subcategory_path.any(filters.category_id)
            )
        )

    if filters.search_text:
        search = f"%{filters.search_text}%"
        query = query.filter(
            or_(
                Product.name[lang].astext.ilike(search),
                Product.description[lang].astext.ilike(search)
            )
        )

    # Sorting
    sort_field = getattr(Product, filters.sort_by, Product.created_at)
    query = query.order_by(sort_field.desc() if filters.sort_dir == 'desc' else sort_field.asc())

    # Count and paginate
    total = query.count()
    results = query.offset(skip).limit(filters.page_size).all()

    items = []
    for product in results:
        items.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "is_active": product.is_active,
            "is_online": product.is_online,
            "created_at": product.created_at,
            "primary_image": product.image_url,
            "is_product_variant": product.is_product_variant,
            "parent_product_id": product.parent_product_id
        })

    return total, items

def get_product_dropdown(db:Session,search:str,current_user:User,lang:str):
    query = db.query(Product).filter(Product.business_id == current_user.business_id)

   # Only Top Level Product
    query = query.filter(Product.parent_product_id.is_(None))


    if search:
        search = search.lower()
        query = query.filter(
            or_(
                Product.name[lang].astext.ilike(search),
                Product.description[lang].astext.ilike(search)
            )
        )

    products = query.order_by(Product.name[lang].astext.asc()).all()

    items = [
        {
            "id": product.id,
            "name": product.name.get(lang) if isinstance(product.name, dict) else product.name,
            "image_url": product.image_url
        }
        for product in products
    ]
    return items

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
