from typing import List, Optional, Union
from datetime import date
from pydantic import BaseModel

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
    parent_product_id: Optional[int] = None
    is_variant: Optional[bool] = False
    
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = False
    is_online: Optional[bool] = False
    selling_price: Optional[float] = None
    low_stock_alert: Optional[int] = None

    category_id: Optional[int] = None
    subcategory_path: Optional[List[int]] = None
    tags:Optional[List[str]] = None

    base_unit: Optional[str] = None
    package_type:Optional[str] = None
    unit_weight:Optional[float] = None
    unit_volume:Optional[float] = None
    dimensions:Optional[dict] = None

    discount_type: Optional[str] = None
    discount_value: Optional[float] = None
    max_discount: Optional[float] = None
    include_tax: Optional[bool] = False
    tax_rate: Optional[float] = None
    hsn_code: Optional[str] = None

    brand: Optional[str] = None
    manufacturer: Optional[str] = None
    origin_country: Optional[str] = None
    
    packed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    purchase_price: Optional[float] = None
    quantity: Optional[int] = None


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

class ProductStockLogFilter(BaseModel):
    product_id: Optional[int] = None
    source:Optional[str] = None
    from_date:Optional[date] = None
    to_date:Optional[date] = None
    page:int
    page_size:int
    sort_by:str = 'transaction_date'
    sort_dir:str = 'desc'


class ProductStockUpdateSchema(BaseModel):
    product_id: int
    batch_id:Optional[int] = None
    quantity: Optional[int] = None
    purchase_price: Optional[float] = None
    source: Optional[str] = None
    source_id: Optional[int] = None
    packed_date: Optional[date] = None
    expiry_date: Optional[date] = None
    is_stock_in:Optional[bool] = False
    notes: Optional[str] = None

class ProductBatchUpdate(BaseModel):
    id: int
    packed_date:Optional[date] = None
    expiry_date:Optional[date] = None
    is_expired:Optional[bool] = None 