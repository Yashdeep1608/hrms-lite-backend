from pydantic import BaseModel,ConfigDict
from typing import Any, Dict, List, Optional
from uuid import UUID

class CustomFieldCreate(BaseModel):
    field_name: str
    field_type: str  # e.g., text, number, date, dropdown
    is_required: bool = False
    options: Optional[List[str]] = None

class CustomFieldUpdate(BaseModel):
    field_name: Optional[str]
    is_required: Optional[bool]
    options: Optional[List[str]] = None

class CustomFieldOut(BaseModel):
    id: UUID
    field_name: str
    field_type: str
    is_required: bool
    options: Optional[List[str]]

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class TagCreate(BaseModel):
    name: str
    color: Optional[str] = None

class TagUpdate(BaseModel):
    name: Optional[str]
    color: Optional[str]

class TagOut(BaseModel):
    id: UUID
    name: str
    color: Optional[str]

    model_config = ConfigDict(from_attributes=True, ser_json_timedelta="iso8601")

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_dynamic: Optional[bool] = False
    business_contact_ids:Optional[List[str]] = None
    filters: Optional[Dict] = None

class GroupUpdate(BaseModel):
    name: Optional[str]
    description: Optional[str]
    business_contact_ids:Optional[List[str]]
    filters: Optional[Dict]
    is_dynamic: Optional[bool]

class GroupOut(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    is_dynamic: bool
    filters: Optional[Dict] = None

    model_config = ConfigDict(from_attributes=True)

class CustomFieldInput(BaseModel):
    field_id: UUID
    value: str

class ContactCreate(BaseModel):
    isd_code: Optional[str]
    phone_number: str
    email: Optional[str] = None
    country_code: Optional[str] = None
    gender: Optional[str] = None
    preferred_language: Optional[str] = 'en'

    first_name: Optional[str] = None
    last_name: Optional[str] = None
    label: Optional[str] = None
    notes: Optional[str] = None
    is_favorite: Optional[bool] = False
    sponsor_id: Optional[UUID] = None

    custom_fields: Optional[List[CustomFieldInput]] = []

class ContactUpdate(BaseModel):
    first_name: Optional[str]
    last_name: Optional[str]
    label: Optional[str]
    notes: Optional[str]
    is_favorite: Optional[bool]
    sponsor_id: Optional[UUID]

    # Editable Contact fields
    email: Optional[str]
    gender: Optional[str]
    preferred_language: Optional[str]

    # Custom field values
    custom_fields: Optional[List[CustomFieldInput]] = []

class ContactFilterRequest(BaseModel):
    page_number: int = 1
    page_size: int = 2
    sort_by: str = "created_at"
    sort_dir: str = "desc"  # or "asc"
    search: Optional[str] = ""
    group_id: Optional[UUID] = None
    filters: Optional[Dict[str, Any]] = None

class AssignContactsGroupsRequest(BaseModel):
    contact_ids: List[UUID]
    group_ids: List[UUID]
    assigned_by: int  # User ID

class AssignContactsTagsRequest(BaseModel):
    contact_ids: List[UUID]
    tag_ids: List[UUID]
    assigned_by: int  # User ID

class CreateLedger(BaseModel):
    business_contact_id:UUID
    entry_type:str
    amount:float
    payment_method:Optional[str] = None
    notes:Optional[str] = None
