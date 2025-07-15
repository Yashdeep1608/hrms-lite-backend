from sqlalchemy import or_,func,and_
from sqlalchemy.orm import Session,joinedload,aliased
from app.models.business import Business
from app.models.product import Product, ProductVariant, ProductImage
from app.schemas.product import ProductCreate, ProductUpdate
from typing import Tuple, List
import hashlib

def hash_sku(company_key: str, product_id: int) -> str:
    raw = f"{company_key.upper()}_{product_id}"
    hash_str = hashlib.sha1(raw.encode()).hexdigest().upper()
    # Remove non-alphanumeric if needed, take first 12 chars
    return ''.join(filter(str.isalnum, hash_str))[:12]

def create_product(db: Session, product_in: ProductCreate):
    product = Product(
        name=product_in.name,
        sku=product_in.sku,
        business_id=product_in.business_id,
        category_id=product_in.category_id,
        subcategory_id=product_in.subcategory_id,
        base_unit=product_in.base_unit,
        description=product_in.description,
        tags=product_in.tags,
        include_tax=product_in.include_tax,
        tax_value=product_in.tax_value,
        is_active=product_in.is_active,
        is_deleted=False  # Default to not deleted
    )
    db.add(product)
    db.flush()  # Get product.id
    # Retrieve company key using business_id
    business = db.query(Business).filter(Business.id == product.business_id).first()
    company_key = business.business_key if business and business.business_key else "UNKNOWN"

    # Generate SKU
    product.sku = hash_sku(company_key, product.id)
    db.commit()  # Commit to save SKU
    # ➕ Add product-level images
    if product_in.images:
        for image_data in product_in.images:
            image = ProductImage(
                product_id=product.id,
                media_url=image_data.media_url,
                media_type=image_data.media_type,
                is_primary=image_data.is_primary
            )
            db.add(image)

    # ➕ Add variants and variant images
    for variant_data in product_in.variants or []:
        variant = ProductVariant(
            product_id=product.id,
            variant_name=variant_data.variant_name,
            attributes = variant_data.attributes,
            min_qty=variant_data.min_qty,
            max_qty=variant_data.max_qty,
            allowed_qty_steps=variant_data.allowed_qty_steps,
            available_qty=variant_data.available_qty,
            purchase_price=variant_data.purchase_price,
            selling_price=variant_data.selling_price,
            discount_type=variant_data.discount_type,
            discount_value=variant_data.discount_value,
        )
        db.add(variant)
        db.flush()

        for image_data in variant_data.images or []:
            image = ProductImage(
                variant_id=variant.id,
                media_url=image_data.media_url,
                media_type=image_data.media_type,
                is_primary=image_data.is_primary
            )
            db.add(image)

    db.commit()
    db.refresh(product)
    return product


def update_product(db: Session, product_in: ProductUpdate):
    product = db.query(Product).filter(Product.id == product_in.id).first()
    if not product:
        raise Exception("Product not found")

    # 🔁 Update product fields (except variants/images)
    for field, value in product_in.model_dump(exclude_unset=True).items():
        if hasattr(product, field) and field not in ("variants", "images"):
            setattr(product, field, value)

    # 🔁 Update product-level images
    if product_in.images is not None:
        db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
        for image_data in product_in.images:
            image = ProductImage(
                product_id=product.id,
                media_url=image_data.media_url,
                media_type=image_data.media_type,
                is_primary=image_data.is_primary
            )
            db.add(image)

    # 🔁 Handle variants
    existing_variants = {v.id: v for v in product.variants}
    received_variant_ids = []

    for variant_data in product_in.variants or []:
        if variant_data.id and variant_data.id in existing_variants:
            variant = existing_variants[variant_data.id]
            for field, value in variant_data.model_dump(exclude_unset=True).items():
                if hasattr(variant, field) and field != "images":
                    setattr(variant, field, value)

            # Replace variant images
            db.query(ProductImage).filter(ProductImage.variant_id == variant.id).delete()
            for image_data in variant_data.images or []:
                image = ProductImage(
                    variant_id=variant.id,
                    media_url=image_data.media_url,
                    media_type=image_data.media_type,
                    is_primary=image_data.is_primary
                )
                db.add(image)

            received_variant_ids.append(variant.id)

        else:
            # ➕ New variant
            variant = ProductVariant(
                product_id=product.id,
                variant_name=variant_data.variant_name,
                attributes = variant_data.attributes,
                min_qty=variant_data.min_qty,
                max_qty=variant_data.max_qty,
                allowed_qty_steps=variant_data.allowed_qty_steps,
                available_qty=variant_data.available_qty,
                purchase_price=variant_data.purchase_price,
                selling_price=variant_data.selling_price,
                discount_type=variant_data.discount_type,
                discount_value=variant_data.discount_value,
            )
            db.add(variant)
            db.flush()

            for image_data in variant_data.images or []:
                image = ProductImage(
                    variant_id=variant.id,
                    media_url=image_data.media_url,
                    media_type=image_data.media_type,
                    is_primary=image_data.is_primary
                )
                db.add(image)

            received_variant_ids.append(variant.id)

    # 🗑️ Delete removed variants
    for variant_id in existing_variants:
        if variant_id not in received_variant_ids:
            db.query(ProductVariant).filter(ProductVariant.id == variant_id).delete()
            db.query(ProductImage).filter(ProductImage.variant_id == variant_id).delete()

    db.commit()
    db.refresh(product)
    return product

def toggle_product_status(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    product.is_active = not product.is_active
    db.commit()
    db.refresh(product)
    return product

def get_product_details(db: Session, product_id: int):
    product = (
        db.query(Product)
        .options(
            joinedload(Product.variants).joinedload(ProductVariant.images)
        )
        .filter(Product.id == product_id)
        .first()
    )
    return product

def get_product_list(
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
    lang: str = 'en'
) -> Tuple[int, List[dict]]:
    skip = (page - 1) * page_size

    # Aliased image for primary image join
    PrimaryImage = aliased(ProductImage)

    # Base query with outer join to fetch only the primary image
    query = (
        db.query(Product, PrimaryImage.media_url.label("primary_image"))
        .outerjoin(
            PrimaryImage,
            and_(
                Product.id == PrimaryImage.product_id,
                PrimaryImage.is_primary == True
            )
        )
        .filter(Product.business_id == business_id)
    )

    query = query.filter(Product.is_deleted == False)  # Exclude soft-deleted products
    # Search filter on localized name/description
    if search_text:
        search = f"%{search_text}%"
        query = query.filter(
            or_(
                Product.name[lang].astext.ilike(search),
                Product.description[lang].astext.ilike(search)
            )
        )

    # Filter by active status
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)

    # Filter by category/subcategory
    if category_id is not None:
        query = query.filter(Product.category_id == category_id)
    if subcategory_id is not None:
        query = query.filter(Product.subcategory_id == subcategory_id)
    # Sorting
    sort_field = getattr(Product, sort_by, Product.created_at)
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
    for product, primary_image in results:
        items.append({
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "primary_image": primary_image
        })

    return total, items

def delete_product(db: Session, product_id: int):
    product = db.query(Product).filter(Product.id == product_id).first()
    product.is_deleted = True
    product.is_active = False  # Optionally deactivate instead of hard delete
    db.commit()
    db.refresh(product)
    return product