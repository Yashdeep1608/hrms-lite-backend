# models/product.py
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, ForeignKey, CheckConstraint,
    Numeric, Boolean, TIMESTAMP, UniqueConstraint,DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from app.db.base import Base

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(JSONB, nullable=False)
    sku = Column(String(50), unique=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    subcategory_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    base_unit = Column(String(10), nullable=True)
    description = Column(JSONB, nullable=False)

    tags = Column(JSONB,nullable = True)
    include_tax = Column(Boolean, default=False) # if True, add tax in amount
    tax_value = Column(Numeric, nullable=True) # if include_tax is True, this is the tax value in %
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean,nullable=False)
    is_deleted = Column(Boolean,nullable=False)
    __table_args__ = (
        CheckConstraint(
            "base_unit IN ('g', 'kg', 'mg', 'ml', 'ltr', 'pcs', 'dozen', 'meter', 'cm', 'inch', 'pack', 'box', 'bottle', 'unit')",
            name="check_base_unit"
        ),
    )

    variants = relationship("ProductVariant", back_populates="products")
    businesses = relationship("Business", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")

     # Explicit relationships
    main_product_category = relationship("Category", foreign_keys=[category_id], back_populates="main_products")
    sub_product_category = relationship("Category", foreign_keys=[subcategory_id], back_populates="sub_products")


class ProductVariant(Base):
    __tablename__ = 'product_variants'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=False)

    variant_name = Column(JSONB, nullable=False)
    attributes = Column(JSONB, nullable=False)  # e.g. {"color": "red", "size": "M"}

    min_qty = Column(Integer, nullable=False)
    max_qty = Column(Integer, nullable=False)
    allowed_qty_steps = Column(JSONB, nullable=False)

    discount_type = Column(String, nullable=True)  # e.g. "percentage", "flat"
    discount_value = Column(Numeric(10, 2), nullable=True)  # e


    available_qty = Column(Integer, nullable=False, default=0)

    purchase_price = Column(Numeric(10, 2))
    selling_price = Column(Numeric(10, 2))
    
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        CheckConstraint('min_qty >= 0', name='check_min_qty'),
        CheckConstraint('max_qty > min_qty', name='check_max_qty'),
        CheckConstraint('available_qty >= 0', name='check_available_qty'),
    )

    products = relationship("Product", back_populates="variants")
    images = relationship("ProductImage", back_populates="variant", cascade="all, delete-orphan")


class ProductImage(Base):
    __tablename__ = 'product_images'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=True)
    variant_id = Column(Integer, ForeignKey('product_variants.id', ondelete='CASCADE'), nullable=True)
    media_url = Column(Text, nullable=False)
    media_type = Column(String,nullable=False)
    is_primary = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="images")
    variant = relationship("ProductVariant", back_populates="images")