from typing import List, Optional, Literal, Dict, Union
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, condecimal


# ---------- Master Data ----------
class ProductMasterDataCreate(BaseModel):
    type: str
    options: List[str]

class ProductMasterDataUpdate(BaseModel):
    id:int
    type: str
    options: Optional[List[str]] = None


# ---------- Custom Fields ----------
class ProductCustomFieldCreate(BaseModel):
    field_name: str
    field_type: str
    is_required: Optional[bool] = False
    is_filterable: Optional[bool] = False
    options: Optional[List[str]] = None
class ProductCustomFieldUpdate(BaseModel):
    id:int
    field_name: str
    field_type: str
    is_required: Optional[bool] = False
    is_filterable: Optional[bool] = False
    options: Optional[List[str]] = None


class ProductCustomFieldValueCreate(BaseModel):
    field_id: int
    value: Optional[Union[str, int, float, bool, date]] = None


# ---------- Product Image ----------
class ProductImageCreate(BaseModel):
    media_url: str
    media_type: str  # "image", "video", etc.


# ---------- Product Create ----------
class ProductBase(BaseModel):
    name: dict
    description: Optional[dict] = None
    image_url: Optional[str] = None
    is_product_variant: Optional[bool] = False

    parent_product_id: Optional[int] = None
    category_id: Optional[int] = None
    subcategory_path: Optional[List[int]] = None

    purchase_price: Optional[float] = None
    selling_price: Optional[float] = None
    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount: Optional[float] = None
    include_tax: Optional[bool] = False
    tax_rate: Optional[float] = None
    hsn_code: Optional[str] = None

    base_unit: Optional[str] = None
    package_type:Optional[str] = None
    stock_qty: Optional[int] = None
    low_stock_alert: Optional[int] = None

    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    packed_date: Optional[date] = None
    expiry_date: Optional[date] = None

    is_active: Optional[bool] = False
    is_online: Optional[bool] = False
    tags:Optional[List[str]] = None

class ProductCreate(ProductBase):
    images: Optional[List[ProductImageCreate]] = []
    custom_field_values: Optional[List[ProductCustomFieldValueCreate]] = []
    variants: Optional[List["ProductCreate"]] = []  # recursive for variant children


ProductCreate.model_rebuild()  # For recursive references

class ProductUpdate(ProductCreate):
    id: Optional[int] = None
class ProductFilters(BaseModel):
    page: int = 1
    page_size: int = 20
    search_text: str = ''
    is_active: Optional[bool] = None
    is_online:Optional[bool] = None,
    sort_by: str = 'created_at'
    sort_dir: str = 'desc'
    category_id: Optional[int] = None
