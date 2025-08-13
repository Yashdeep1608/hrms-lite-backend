# models/product.py
from datetime import datetime, timezone
from sqlalchemy import (
    ARRAY, Column, Date, Enum, Integer, String, Text, ForeignKey,
    Numeric, Boolean,DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from app.db.base import Base
from app.models.enums import ProductStockSource

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    parent_product_id = Column(Integer, ForeignKey("products.id"), nullable=True)  # master -> null
    is_variant = Column(Boolean, default=False)  # optional, clarity

    # Basic Info
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    slug = Column(String(255), unique=True, nullable=True)
    sku = Column(String(100), unique=True, nullable=True)
    image_url = Column(String, unique=True, nullable=True)
    barcode = Column(String, unique=True, nullable=True)
    qrcode = Column(String, unique=True, nullable=True)
    selling_price = Column(Numeric(10,2), nullable=True)
    low_stock_alert = Column(Integer,default=0)
    is_active = Column(Boolean, default=True)
    is_online = Column(Boolean, default=True)
    is_deleted = Column(Boolean, default=False)

    # Category / Tags
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    subcategory_path = Column(ARRAY(Integer), nullable=True)
    tags = Column(JSONB, nullable=True)

    # Units / Packaging
    base_unit = Column(String(50), nullable=False)
    package_type = Column(String(50), nullable=True)
    unit_weight = Column(Numeric(10,2), nullable=True)
    unit_volume = Column(Numeric(10,2), nullable=True)
    dimensions = Column(JSONB, nullable=True)  # length, width, height

    # Tax / Discount
    discount_type = Column(String, nullable=True)
    discount_value = Column(Numeric, nullable=True)
    max_discount = Column(Numeric, nullable=True)
    include_tax = Column(Boolean, default=False)
    tax_rate = Column(Numeric(5,2), nullable=True)
    hsn_code = Column(String(20), nullable=True)

    # Brand / Manufacturer / Origin
    brand = Column(String(255), nullable=True)
    manufacturer = Column(String(255), nullable=True)
    origin_country = Column(String(10), nullable=True)

    # Audit
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    parent = relationship(
        "Product",
        remote_side=[id],
        backref=backref("variants", lazy="selectin")
    )
    custom_field_values = relationship("ProductCustomFieldValue", back_populates="product", cascade="all, delete")
    batches = relationship("ProductBatch", back_populates="product", cascade="all, delete-orphan")
    stock_logs = relationship("ProductStockLog", back_populates="product", cascade="all, delete-orphan")
    pack_options = relationship("ProductPackOption", back_populates="product", cascade="all, delete-orphan")
    businesses = relationship("Business", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_product")

class ProductBatch(Base):
    __tablename__ = "product_batches"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_code = Column(String, nullable=True)
    purchase_price = Column(Numeric(10,2), nullable=False)
    quantity = Column(Integer, nullable=False)
    packed_date = Column(Date, nullable=True)
    expiry_date = Column(Date, nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    is_expired = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="batches")
    stock_logs = relationship("ProductStockLog", back_populates="batch", cascade="all, delete-orphan")

class ProductPackOption(Base):
    __tablename__ = "product_pack_options"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    pack_quantity = Column(Integer, nullable=False)  # 2, 6, etc.
    additional_discount = Column(Numeric(10,2), nullable=True)  # optional

    product = relationship("Product", back_populates="pack_options")

class ProductCustomField(Base):
    __tablename__ = 'product_custom_fields'

    id = Column(Integer, primary_key=True,index=True)
    business_id = Column(Integer, nullable=False, index=True)
    field_name = Column(String, nullable=False)
    field_type = Column(String, nullable=False)  # 'string', 'number', 'date', 'dropdown', 'boolean'
    is_required = Column(Boolean, default=False)
    is_filterable = Column(Boolean, default=False)  # Optional: mark this field as filter in product listing
    options = Column(JSONB, nullable=True)  # Only if field_type == 'dropdown'

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    values = relationship("ProductCustomFieldValue", back_populates="field", cascade="all, delete", passive_deletes=True)

class ProductCustomFieldValue(Base):
    __tablename__ = 'product_custom_field_values'

    id = Column(Integer, primary_key=True,index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete="CASCADE"), nullable=False)
    field_id = Column(Integer, ForeignKey('product_custom_fields.id', ondelete="CASCADE"), nullable=False)
    value = Column(Text, nullable=True)

    product = relationship("Product", back_populates="custom_field_values")
    field = relationship("ProductCustomField", back_populates="values", passive_deletes=True)
    
class ProductImage(Base):
    __tablename__ = 'product_images'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=True)
    media_url = Column(Text, nullable=False)
    media_type = Column(String,nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="images")

class ProductStockLog(Base):
    __tablename__ = "product_stock_logs"

    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    batch_id = Column(Integer, ForeignKey("product_batches.id"), nullable=True)
    is_stock_in = Column(Boolean, default=False)
    quantity = Column(Integer, nullable=False)
    stock_before = Column(Integer, nullable=True)
    stock_after = Column(Integer, nullable=True)
    source = Column(Enum(ProductStockSource), nullable=True)  # order, return, etc.
    unit_price = Column(Numeric(10,2), nullable=True)
    total_amount = Column(Numeric(10,2), nullable=True)
    source_id = Column(Integer, nullable=True)
    note = Column(String, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="stock_logs")
    batch = relationship("ProductBatch", back_populates="stock_logs")
