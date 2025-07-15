from typing import List, Optional, Literal, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict, condecimal


# ----------------------------
# Product Image Schema
# ----------------------------
class ProductImageBase(BaseModel):
    media_url: str # URL of the image
    media_type: str # Type of media (e.g., 'image', 'video')
    is_primary: Optional[bool] = False # Indicates if this is the primary image


class ProductImageCreate(ProductImageBase):
    product_id: Optional[int] = None
    variant_id: Optional[int] = None


class ProductImageOut(ProductImageBase):
    id: int
    product_id: Optional[int] = None
    variant_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


# ----------------------------
# Product Variant Schema
# ----------------------------
class ProductVariantBase(BaseModel):
    variant_name: Dict[str, str]  # JSONB variant name for multilingual support
    attributes: Optional[Dict[str, str]] = None  # JSONB attributes for variant (e.g., {"color": "red", "size": "M"})
    min_qty: int # Minimum quantity for purchase
    max_qty: int # Maximum quantity for purchase
    allowed_qty_steps: Optional[List[int]] # Allowed quantity steps for purchase
    available_qty: Optional[int] = 0 # Available quantity in stock
    discount_type: Optional[Literal["percentage", "flat"]] = None  # e.g. "percentage", "flat"
    discount_value: Optional[condecimal(max_digits=10, decimal_places=2)] = None  # type: ignore # e.g. 10 for 10% or 100 for flat $100 off
    purchase_price: Optional[condecimal(max_digits=10, decimal_places=2)]  # type: ignore 
    selling_price: Optional[condecimal(max_digits=10, decimal_places=2)]  # type: ignore
    
class ProductVariantCreate(ProductVariantBase):
    images: Optional[List[ProductImageCreate]] = None


class ProductVariantUpdate(ProductVariantBase):
    id: Optional[int]
    images: Optional[List[ProductImageCreate]] = None


class ProductVariantOut(ProductVariantBase):
    id: int
    images: List[ProductImageOut]
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


# ----------------------------
# Product Base Schema
# ----------------------------
class ProductBase(BaseModel):
    name: Dict[str, str] #JSONB name for multilingual support
    sku: Optional[str] = None # SKU for product
    business_id: int #Business ID to which the product belongs
    category_id: int # Category ID for product categorization
    subcategory_id: Optional[int] = None # Optional subcategory ID
    base_unit: Optional[Literal['g', 'kg', 'ml', 'ltr', 'pcs', 'dozen']] # Base unit of measurement
    description: Dict[str, str] # JSONB description for multilingual support
    is_active: bool # Indicates if the product is active
    tags:Optional[List[str]]
    include_tax:Optional[bool] # if True, add tax in amount
    tax_value:Optional[int]


# ----------------------------
# Create & Update Schemas
# ----------------------------
class ProductCreate(ProductBase):
    variants: Optional[List[ProductVariantCreate]] = None
    images: Optional[List[ProductImageCreate]] = None


class ProductUpdate(ProductBase):
    id: int
    variants: Optional[List[ProductVariantUpdate]] = None
    images: Optional[List[ProductImageCreate]] = None


# ----------------------------
# Response Schemas
# ----------------------------
class ProductOut(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    variants: List[ProductVariantOut]
    images: List[ProductImageOut]

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


class ProductListOut(BaseModel):
    id: int
    name: Dict[str, str]
    sku: Optional[str]
    is_active: bool
    primary_image: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")


class ProductListResponse(BaseModel):
    total: int
    items: List[ProductListOut]
