# models/product.py
from datetime import datetime, timezone
from sqlalchemy import (
    ARRAY, Column, Date, Enum, Integer, String, Text, ForeignKey,
    Numeric, Boolean,DateTime
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, backref
from app.db.base import Base

class Product(Base):
    __tablename__ = 'products'

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id'), nullable=False)

    # Basic
    name = Column(String(100), nullable=False)
    description = Column(String(1000), nullable=True)
    image_url = Column(String, nullable=False)
    is_product_variant = Column(Boolean,default=False)

    # Variant Linking / Category Linking 
    parent_product_id = Column(Integer,ForeignKey("products.id"),nullable=True)
    category_id = Column(Integer, ForeignKey('categories.id'), nullable=False)
    subcategory_path = Column(ARRAY(Integer))
    
    # Pricing and Tax
    purchase_price = Column(Numeric(10, 2),nullable=True)
    selling_price = Column(Numeric(10, 2),nullable=True)
    discount_type = Column(String, nullable=True)  # e.g. "percentage", "flat"
    discount_value = Column(Numeric, nullable=True)  # e.g. 10 for 10% or 100 for flat $100 off
    max_discount = Column(Numeric, nullable=True)
    include_tax = Column(Boolean, default=False)
    tax_rate = Column(Numeric(5, 2),nullable=True)  # GST %
    hsn_code = Column(String(10),nullable=True)     # Government classification
    
    # Units & Packaging
    base_unit = Column(String(20), nullable=False)
    package_type = Column(String(50),nullable=False)         # Example: "g", "ml", "piece"
    stock_qty = Column(Integer,nullable=True)  
    low_stock_alert = Column(Integer,nullable=True)

    # Legal Compliance Fields
    brand = Column(String(255),nullable=True)             # Mandatory in many sectors
    manufacturer = Column(String(255),nullable=True)      # May be same as brand
    packed_date = Column(Date,nullable=True)              # Packed on (optional for pre-packaged goods)
    expiry_date = Column(Date,nullable=True)              # Expiry (for food/pharma)
    

    #Status an Field
    is_active = Column(Boolean,default=False)
    is_deleted = Column(Boolean,default=False)
    is_online = Column(Boolean,default=False)



    #Others 
    slug = Column(String(255), unique=True, nullable=True)
    sku = Column(String(100), unique=True, nullable=True)
    barcode = Column(String(100), unique=True, nullable=True)
    qr_code = Column(String, nullable=True)

    tags = Column(JSONB, nullable=True) # Searching Tags
    
    #Audit Log
    created_by_user_id  = Column(Integer, ForeignKey("users.id"), nullable=True)

    #Time Stamp
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))
   
   

    businesses = relationship("Business", back_populates="products")
    images = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan")
    created_by = relationship("User", foreign_keys=[created_by_user_id], back_populates="created_product")
    product_category = relationship("Category", foreign_keys=[category_id], back_populates="products")
    parent = relationship(
        "Product",
        remote_side=[id],
        lazy="select",  # or "joined" if you always need parent eagerly
        backref=backref("variants", lazy="selectin"),
        cascade="none"
    )
    custom_field_values = relationship("ProductCustomFieldValue", back_populates="product", cascade="all, delete", passive_deletes=True)


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

class ProductMasterData(Base):
    __tablename__ = 'product_master_data'

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), nullable=False)
    
    type = Column(Enum('base_unit', 'package_type', 'brand', 'manufacturer', name='master_type'), nullable=False)
    options = Column(JSONB, nullable=False)  # e.g., "ml", "Nestle", "Box", etc.

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
class ProductImage(Base):
    __tablename__ = 'product_images'

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey('products.id', ondelete='CASCADE'), nullable=True)
    media_url = Column(Text, nullable=False)
    media_type = Column(String,nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    product = relationship("Product", back_populates="images")
