from datetime import date
from decimal import Decimal
from slugify import slugify
from sqlalchemy import any_, asc, desc, distinct, not_, or_,func,and_, select
from sqlalchemy.orm import Session,joinedload,aliased
from app.helpers.utils import generate_barcode, generate_qr_code
from app.models.business import Business
from app.models.enums import ProductStockSource, ProductStockStatus
from app.models.product import *
from app.models.user import User
from app.schemas.product import *
from typing import Optional, Tuple, List
import hashlib
from sqlalchemy.orm import subqueryload

def hash_sku(company_key: str, product_id: int) -> str:
    raw = f"{company_key.upper()}_{product_id}"
    hash_str = hashlib.sha1(raw.encode()).hexdigest().upper()
    # Remove non-alphanumeric if needed, take first 12 chars
    return ''.join(filter(str.isalnum, hash_str))[:12]
def calculate_final_price(product:Product):
    selling_price = product.selling_price or Decimal(0)
    discount_type = product.discount_type
    discount_value = product.discount_value or Decimal(0)
    max_discount = product.max_discount or Decimal(0)
    include_tax = product.include_tax
    tax_rate = product.tax_rate or Decimal(0)

    discount_amount = Decimal(0)

    if discount_type == "percentage":
        discount_amount = selling_price * discount_value / 100
    elif discount_type == "flat":
        discount_amount = discount_value

    if max_discount > 0:
        discount_amount = min(discount_amount, max_discount)

    price_after_discount = selling_price - discount_amount

    # Add tax if not included
    if not include_tax and tax_rate > 0:
        tax_amount = price_after_discount * tax_rate / 100
    else:
        tax_amount = Decimal(0)

    final_price = price_after_discount + tax_amount
    if final_price < 0:
        final_price = 0
    return round(final_price, 2)
def generate_batch_code(business_id: int, product_id: int, batch_number: int = 1) -> str:
    product_code = hex(product_id)[2:].upper()  # e.g., product_id=123 -> '7B'
    batch_seq = f"{batch_number:02d}"
    batch_code = f"B{hex(business_id)[2:].upper()}-P{product_code}-{batch_seq}"
    return batch_code
def get_stock_status(total_stock: int, low_stock_alert: int) -> str:
    if total_stock <= 0:
        return "Out of Stock"
    elif total_stock <= low_stock_alert:
        return "Low Stock"
    return "In Stock"

def create_product(db: Session, product_in: ProductCreate, current_user: User):
    parent_product = None

    # If this is a variant, fetch parent and inherit fields if not set
    if product_in.parent_product_id:
        parent_product = db.query(Product).filter(Product.id == product_in.parent_product_id).first()

    def inherit(field_name, fallback=None):
        return getattr(product_in, field_name, None) or (getattr(parent_product, field_name) if parent_product else fallback)
    
    product = Product(
        
        business_id=current_user.business_id,
        created_by_user_id=current_user.id,
        parent_product_id=product_in.parent_product_id,
        is_variant=product_in.is_variant,

        name=product_in.name,
        description=product_in.description or None,
        image_url=inherit("image_url"),
        is_active=product_in.is_active or False,
        is_deleted=False,
        is_online=product_in.is_online or False,
        selling_price=product_in.selling_price,
        low_stock_alert=product_in.low_stock_alert,
        
        category_id=inherit("category_id"),
        subcategory_path=inherit("subcategory_path"),
        tags=product_in.tags,
        
        base_unit=inherit("base_unit"),
        package_type=inherit("package_type"),
        unit_weight=product_in.unit_weight,
        unit_volume=product_in.unit_volume,
        dimensions=product_in.dimensions,
        
        discount_type=product_in.discount_type,
        discount_value=product_in.discount_value,
        max_discount=product_in.max_discount,
        include_tax=inherit("include_tax", False),
        tax_rate=inherit("tax_rate", 0.0),
        hsn_code=inherit("hsn_code"),
       
        brand=inherit("brand"),
        manufacturer=inherit("manufacturer"),
        origin_country=product_in.origin_country or "India"
    )

    db.add(product)
    db.flush()  # Get product.id for SKU generation

    # Generate SKU, barcode, QR
    business = db.query(Business).filter(Business.id == current_user.business_id).first()
    company_key = business.business_key if business and business.business_key else "UNKNOWN"
    product.slug = f"{slugify(product.name)}-{hex(product.id)[2:]}"
    product.sku = hash_sku(company_key, product.id)
    product.barcode = generate_barcode(product.sku)
    product.qrcode = generate_qr_code(product.sku)

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

    # Add Product Batch
    if product_in.quantity > 0:
        product_batch = ProductBatch(
            product_id = product.id,
            batch_code = generate_batch_code(current_user.business_id,product.id,1),
            purchase_price = product_in.purchase_price,
            quantity = product_in.quantity,
            packed_date = product_in.packed_date,
            expiry_date = product_in.expiry_date
        )
        db.add(product_batch)
    # Recursively create variants
    for variant_data in product_in.variants or []:
        variant_data.parent_product_id = product.id
        variant_data.is_variant = True
        create_product(db, variant_data, current_user)

    add_product_stock_log(
        db=db,
        product_id=product.id,
        quantity=product_batch.quantity,
        is_stock_in=True,
        batch_id=product_batch.id,
        stock_before=0,
        unit_price=product_batch.purchase_price,
        stock_after=product_batch.quantity,
        source=ProductStockSource.MANUAL,
        source_id=None,
        created_by=current_user.id if current_user.id else None,
        notes=f"Product added manually from product {product.sku}"
    )

    db.commit()
    db.refresh(product)
    return product

def update_product(db: Session, product_id: int, product_in: ProductUpdate, current_user: User):
    # Fetch product
    product = db.query(Product).filter(
        Product.id == product_id,
        Product.business_id == current_user.business_id
    ).first()
    if not product:
        raise Exception("Product not found")

    # Only update fields that are allowed
    update_data = product_in.model_dump(exclude_unset=True)
    allowed_fields = [
        "name", "description", "image_url", "is_active", "is_online",
        "tags", "selling_price", "discount_type", "discount_value", "max_discount",
        "include_tax", "tax_rate","hsn_code" ,"category_id", "subcategory_path",
        "base_unit", "package_type", "unit_weight", "unit_volume", "dimensions",
        "brand", "manufacturer", "origin_country"
    ]

    if not product_in.discount_type:
        product.discount_value = 0
        product.max_discount = 0

    for field, value in update_data.items():
        if field in allowed_fields:
            setattr(product, field, value)

    # Regenerate slug if name changed
    if "name" in update_data:
        product.slug = f"{slugify(product.name)}-{hex(product.id)[2:]}"

    # Update images (only for non-variant products)
    if "images" in update_data and not product.parent_product_id:
        db.query(ProductImage).filter(ProductImage.product_id == product.id).delete()
        for img in update_data["images"]:
            db.add(ProductImage(
                product_id=product.id,
                media_url=img.media_url,
                media_type=img.media_type
            ))

    # Update custom field values
    if "custom_field_values" in update_data:
        db.query(ProductCustomFieldValue).filter(ProductCustomFieldValue.product_id == product.id).delete()
        for cfv in update_data["custom_field_values"]:
            db.add(ProductCustomFieldValue(
                product_id=product.id,
                field_id=cfv['field_id'],
                value=str(cfv['value']) or None
            ))

    # Commit changes
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
    # Fetch main product
    main_product = (
        db.query(Product)
        .options(
            subqueryload(Product.images),
            subqueryload(Product.custom_field_values),
            subqueryload(Product.batches),
            subqueryload(Product.pack_options),
            subqueryload(Product.stock_logs),
            subqueryload(Product.variants).joinedload(Product.custom_field_values),
        )
        .filter(Product.id == product_id)
        .first()
    )

    if not main_product:
        return None

    # Fetch all child products (variants/children)
    main_product.variants = (
        db.query(Product)
        .options(
            subqueryload(Product.images),
            subqueryload(Product.custom_field_values),
            subqueryload(Product.batches),
            subqueryload(Product.pack_options),
            subqueryload(Product.stock_logs),
        )
        .filter(Product.parent_product_id == product_id)
        .all()
    )

    # Sort batches and pack options for clean UI
    main_product.batches = sorted(main_product.batches, key=lambda x: (x.expiry_date or date.max))

    return main_product

def get_product_list(
    db: Session,
    filters: ProductFilters,
    current_user: User,
) -> Tuple[int, List[dict]]:
    skip = (filters.page - 1) * filters.page_size

    # Base query
    query = (
        db.query(Product)
        .filter(
            Product.business_id == current_user.business_id,
            Product.is_deleted == False
        )
        .options(joinedload(Product.parent))  # preload parent
    )

    # Active filter
    if filters.is_active is not None:
        query = query.filter(Product.is_active == filters.is_active)

    # Category filter (supports subcategories)
    if filters.category_id is not None:
        query = query.filter(
            or_(
                Product.category_id == filters.category_id,
                Product.subcategory_path.any(filters.category_id)
            )
        )

    # Search filter (name, description, tags array)
    if filters.search_text:
        search = f"%{filters.search_text}%"
        query = query.filter(
            or_(
                Product.name.ilike(search),
                Product.description.ilike(search),
                func.array_to_string(Product.tags, ',').ilike(search)  # search inside tags array
            )
        )

    # Sorting
    sort_field = getattr(Product, filters.sort_by, Product.created_at)
    query = query.order_by(
        sort_field.desc() if filters.sort_dir == 'desc' else sort_field.asc()
    )

    # Count before pagination
    total = query.count()

    # Fetch results with pagination
    results = query.offset(skip).limit(filters.page_size).all()

    # Serialize response
    items = [
        {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "is_active": product.is_active,
            "is_online": product.is_online,
            "created_at": product.created_at,
            "primary_image": product.image_url,
            "is_variant": product.is_variant,
            "parent_product_id": product.parent_product_id,
            "parent_name": product.parent.name if product.is_variant and product.parent else None
        }
        for product in results
    ]

    return total, items

def get_product_dropdown(db:Session,is_parent:bool,search:str,current_user:User):
    query = db.query(Product).filter(Product.business_id == current_user.business_id,Product.is_deleted == False)

    # Only Top Level Product
    if is_parent:
        query = query.filter(Product.parent_product_id.is_(None))
        
    if search:
        search = search.lower()
        query = query.filter(
            or_(
                Product.name.ilike(search),
                Product.description.ilike(search)
            )
        )

    products = query.order_by(Product.name.asc()).all()

    items = [
        {
            "id": product.id,
            "name": product.name,
            "image_url": product.image_url,
            "final_price": float(calculate_final_price(product))
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

def get_product_stats(db: Session, product_id: int, current_user: User):
    # Get product
    product = (
        db.query(Product)
        .filter(Product.id == product_id, Product.business_id == current_user.business_id)
        .first()
    )
    if not product:
        return {"error": "Product not found"}

    # 1️⃣ Calculate current stock from non-expired batches
    current_stock = (
        db.query(func.coalesce(func.sum(ProductBatch.quantity), 0))
        .filter(
            ProductBatch.product_id == product_id,
            ProductBatch.is_expired != True 
        )
        .scalar()
    )
    
    # 2️⃣ Stock Status
    if current_stock <= 0:
        stock_status = ProductStockStatus.OUT_OF_STOCK
    elif product.low_stock_alert and current_stock <= product.low_stock_alert:
        stock_status = ProductStockStatus.LOW_STOCK
    else:
        stock_status = ProductStockStatus.IN_STOCK

    # 3️⃣ Average purchase price from available batches (weighted)
    purchase_price_data = (
        db.query(
            func.coalesce(
                func.sum(ProductBatch.purchase_price * ProductBatch.quantity), 0
            ).label("total_value"),
            func.coalesce(func.sum(ProductBatch.quantity), 0).label("total_qty")
        )
        .filter(
            ProductBatch.product_id == product_id,
        )
        .first()
    )
    avg_purchase_price = (
        Decimal(purchase_price_data.total_value) / purchase_price_data.total_qty
        if purchase_price_data.total_qty > 0 else Decimal(0)
    )

    # 4️⃣ Final Price after Discount
    selling_price = product.selling_price or Decimal(0)
    if product.discount_type == "percentage":
        discount_amount = selling_price * (product.discount_value or Decimal(0)) / 100
    elif product.discount_type == "flat":
        discount_amount = product.discount_value or Decimal(0)
    else:
        discount_amount = Decimal(0)

    if product.max_discount:
        discount_amount = min(discount_amount, product.max_discount)

    final_price = selling_price - discount_amount

    # 5️⃣ Tax Adjustment
    if not product.include_tax and product.tax_rate:
        final_price += (final_price * product.tax_rate / 100)

    # 6️⃣ Profit per Unit
    profit_per_unit = final_price - avg_purchase_price
    expired_stocks = (
        db.query(
            func.coalesce(
                func.sum(ProductBatch.quantity), 0
            ).label("stocks")
        )
        .filter(
            ProductBatch.product_id == product_id,
            ProductBatch.is_expired == True
        )
        .first()
    )
    # Get total orders, qty, revenue
    stats = (
        db.query(
            func.count(ProductStockLog.source_id).label("total_orders"),
            func.coalesce(func.sum(ProductStockLog.quantity), 0).label("total_qty"),
            func.coalesce(func.sum(ProductStockLog.total_amount), 0).label("total_revenue"),
            # Historical net profit: sum(selling_price - purchase_price) * qty
            func.coalesce(func.sum(
                (ProductStockLog.unit_price - ProductBatch.purchase_price) * ProductStockLog.quantity
            ), 0).label("net_profit")
        )
        .join(ProductBatch, ProductBatch.id == ProductStockLog.batch_id)
        .filter(
            ProductStockLog.product_id == product_id,
            ProductStockLog.source == ProductStockSource.ORDER
        )
        .first()
    )

    return {
        "product_id": product.id,
        "stock_status": stock_status,
        "current_stock": int(current_stock),
        "expired_stocks": int(expired_stocks.stocks),
        "avg_purchase_price": float(avg_purchase_price),
        "final_price": float(final_price),
        "profit_per_unit": float(profit_per_unit),
        "total_orders": int(stats.total_orders or 0),
        "total_qty_sold": int(stats.total_qty or 0),
        "total_revenue": float(stats.total_revenue),
        "net_profit": float(stats.net_profit or 0)
    }

def add_product_stock_log(
    db: Session,
    product_id: int,
    quantity: float,
    is_stock_in: bool,
    batch_id:Optional[int] = None,
    stock_before: Optional[float] = None,
    unit_price:Optional[float] = 0.00,
    stock_after: Optional[float] = None,
    source: Optional[str] = None,
    source_id: Optional[int] = None,
    created_by: Optional[int] = None,
    notes: Optional[str] = None
) -> None:
    # Only fetch product if needed
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise ValueError(f"Product with ID {product_id} not found")

    if stock_before is None or stock_after is None:
        stock_before = sum(b.quantity for b in product.batches)  # batch-based
        stock_after = stock_before + quantity if is_stock_in else stock_before - quantity

    # Determine unit price based on source
    if not is_stock_in and unit_price <= 0:
        # Stock out (selling) → get selling price at the moment
        unit_price = calculate_final_price(product)

    total_amount = round(unit_price * quantity, 2)

    # Generate note
    direction = "Stock-In" if is_stock_in else "Stock-Out"
    source_str = f" via {source.upper()}" if source else ""
    ref_str = f" (Ref ID: {source_id})" if source_id else ""
    note = notes if notes else f"{direction} of {quantity} units{source_str}{ref_str}"

    log = ProductStockLog(
        product_id=product_id,
        batch_id = batch_id,
        quantity=quantity,
        is_stock_in=is_stock_in,
        stock_before=stock_before,
        stock_after=stock_after,
        source=ProductStockSource(source) if source else None,
        source_id=source_id,
        note=note,
        created_by=created_by,
        unit_price=unit_price,
        total_amount=total_amount
    )
    db.add(log)

def get_product_stock_logs(
    db: Session, 
    filters: ProductStockLogFilter, 
    current_user: User
):
    
    # Base query
    query = db.query(ProductStockLog)

    # Apply filters
    if filters.product_id:
        query = query.filter(ProductStockLog.product_id == filters.product_id)

    if filters.source:
        query = query.filter(ProductStockLog.source == filters.source)

    if filters.from_date:
        query = query.filter(ProductStockLog.transaction_date >= filters.from_date)

    if filters.to_date:
        query = query.filter(ProductStockLog.transaction_date <= filters.to_date)

    # Total count before pagination
    total_count = query.count()

    # Sorting
    sort_column = getattr(ProductStockLog, filters.sort_by, None)
    if not sort_column:
        sort_column = ProductStockLog.transaction_date  # fallback

    if filters.sort_dir.lower() == "asc":
        query = query.order_by(sort_column.asc())
    else:
        query = query.order_by(sort_column.desc())

    # Pagination
    offset = (filters.page - 1) * filters.page_size
    logs = query.offset(offset).limit(filters.page_size).all()

    return {
        "total": total_count,
        "items": logs
    }

def update_product_stock(db: Session, data: ProductStockUpdateSchema,current_user:User):
    # Fetch product
    unit_price = 0
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise ValueError(f"Product with ID {data.product_id} not found")

    is_stock_in = False
    if data.source in [ProductStockSource.MANUAL, ProductStockSource.ADJUSTMENT]:
        is_stock_in = data.is_stock_in
    else:
        is_stock_in = data.source in [
            ProductStockSource.SUPPLY,
            ProductStockSource.RETURN,
            ProductStockSource.TRANSFER_IN,
            ProductStockSource.COMBO_BREAK,
            ProductStockSource.SYSTEM_CORRECTION,
        ]
    # === Batch Logic ===
    batch = None
    if is_stock_in:
        batch_count = db.query(ProductBatch).filter(ProductBatch.product_id == product.id).count()
        batch = ProductBatch(
            product_id=data.product_id,
            batch_code = generate_batch_code(product.business_id,product.id,batch_count+1 if batch_count else 1),
            quantity=data.quantity,
            purchase_price=Decimal(data.purchase_price or 0),
            packed_date=data.packed_date,
            expiry_date=data.expiry_date
        )
        db.add(batch)
        unit_price = batch.purchase_price
    else:
        # Stock out → reduce from batch
        batch = db.query(ProductBatch).filter(ProductBatch.id == data.batch_id).first()
        if not batch:
            raise ValueError("Batch ID is required for stock-out")
        if batch.quantity < data.quantity:
            raise ValueError(f"Not enough stock in batch {batch.id}")
        batch.quantity -= data.quantity
        unit_price = batch.quantity * calculate_final_price(Product)

    db.flush()
    stock_before = (
        db.query(func.coalesce(func.sum(ProductBatch.quantity), 0))
        .filter(
            ProductBatch.product_id == data.product_id,
            ProductBatch.is_expired == False
        )
        .scalar()
    )
    # Stock log
    add_product_stock_log(
        db=db,
        product_id=data.product_id,
        quantity=data.quantity,
        is_stock_in=is_stock_in,
        batch_id=batch.id if batch else None,
        stock_before=stock_before,
        unit_price=unit_price,
        stock_after=stock_before + data.quantity if is_stock_in else stock_before - data.quantity,
        source=data.source,
        source_id=data.source_id,
        created_by=current_user.id if current_user.id else None,
        notes=data.notes
    )

    db.commit()
    return {
        "product_id": product.id,
        "batch_id": batch.id if batch else None,
        "stock_before": stock_before,
        "stock_after": stock_before + data.quantity if is_stock_in else stock_before - data.quantity,
        "unit_price": float(unit_price or 0)
    }

def update_product_batch(db: Session, data: ProductBatchUpdate):
    batch = db.query(ProductBatch).filter(ProductBatch.id == data.id).first()
    batch.expiry_date = data.expiry_date or None
    batch.packed_date = data.packed_date or None
    batch.is_expired = data.is_expired or False
    db.commit()
    return batch

def get_product_batches(db:Session,product_id:int):
    return db.query(ProductBatch).filter(ProductBatch.product_id == product_id).all()

def get_product_stock_report(
    db: Session,
    business_id: int,
    filters: StockReportFilter
) :

    # Base query with aggregation
    query = (
        db.query(
            Product.id,
            Product.name,
            Product.image_url,
            Product.low_stock_alert,
            func.coalesce(func.sum(ProductBatch.quantity), 0).label("available_stock"),
        )
        .join(Product.batches)
        .filter(Product.business_id == business_id)
        .group_by(Product.id)
    )

    # ✅ Apply search filter
    if filters.search:
        query = query.filter(
            or_(
                Product.name.ilike(f"%{filters.search}%"),
                Product.description.ilike(f"%{filters.search}%")
            )
        )

    # Category filter (supports subcategories)
    if filters.category_id is not None:
        query = query.filter(
            or_(
                Product.category_id == filters.category_id,
                Product.subcategory_path.any(filters.category_id)
            )
        )

    # Sorting
    sort_column = {
        "name": Product.name,
        "stock": func.coalesce(func.sum(ProductBatch.quantity), 0),
    }.get(filters.sort_by, Product.name)

    if filters.sort_dir == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # Pagination
    total = query.count()
    results = (
        query
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
        .all()
    )

    # Transform into response
    products = []
    for row in results:
        stock_status = get_stock_status(row.available_stock, row.low_stock_alert)
        if filters.status and filters.status.lower().replace(" ", "_") not in stock_status.lower().replace(" ", "_"):
            continue

        products.append({
            "id":row.id,
            "name":row.name,
            "image_url":row.image_url,
            "available_stock":row.available_stock,
            "stock_status":stock_status,
        })

    return {
        "total":total,
        "items":products
    }
