from pydantic import BaseModel, HttpUrl
from typing import Optional, Literal
from datetime import datetime

class BannerBase(BaseModel):
    title: Optional[str] = None
    image_url: HttpUrl
    link_type: Optional[str] = None
    link_target_id: Optional[int] = None
    external_url: Optional[str] = None
    position: Optional[str] = None
    display_order: Optional[int] = 0
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: Optional[bool] = True

class BannerCreate(BannerBase):
    pass

class BannerUpdate(BaseModel):
    title: Optional[str] = None
    image_url: Optional[str] = None
    link_type: Optional[str] = None
    link_target_id: Optional[int] = None
    external_url: Optional[str] = None
    position: Optional[str] = None
    display_order: Optional[int] = None
    start_datetime: Optional[datetime] = None
    end_datetime: Optional[datetime] = None
    is_active: Optional[bool] = None

class BannerFilters(BaseModel):
    search: Optional[str] = None  # title or link_text
    type: Optional[str] = None    # e.g., 'product', 'service', etc.
    is_active: Optional[bool] = None

    from_date: Optional[datetime] = None
    to_date: Optional[datetime] = None

    sort_by: Optional[str] = 'created_at'  # or 'title'
    sort_dir: Optional[str] = 'desc'
    page: int = 1
    page_size: int = 10