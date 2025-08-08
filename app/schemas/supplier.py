from datetime import date
from typing import List, Optional
from pydantic import BaseModel

class AddEditSupplier(BaseModel):
    name:Optional[str] = None
    isd_code:Optional[str] = None
    phone:Optional[str] = None
    email:Optional[int] = None
    address:Optional[int] = None
    pan_number:Optional[int] = None
    gst_number:Optional[int] = None
    
    notes:Optional[str] = None

class PurchaseItemRequest(BaseModel):
    product_id:int
    quantity:int
    unit_price:float
    tax_rate:float
    tax_amount :float
    total_amount:float

class TransactionRequest(BaseModel):
    supplier_id:Optional[int] = None
    purchase_id:Optional[int] = None
    transaction_date:date
    transaction_type:str
    amount:float
    payment_method:str
    notes:Optional[str] = None

class AddSupplierPurchase(BaseModel):
    supplier_id: int
    supplier_invoice_number:Optional[str] = None
    file_url :Optional[str] = None
    purchase_date: date
    taxable_amount:float
    tax_rate:float
    total_tax_amount:float
    total_amount:float
    notes:Optional[str] = None
    items:List[PurchaseItemRequest]
    transactions:List[TransactionRequest]

class SupplierFilters(BaseModel):
    search:Optional[str] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'

class SupplierPurchaseFilters(BaseModel):
    search:Optional[str] = None
    from_date:Optional[date] = None
    to_date:Optional[date] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'

class SupplierTransactionFilters(BaseModel):
    purchase_id:Optional[str] = None
    payment_method:Optional[str] = None
    from_date:Optional[date] = None
    to_date:Optional[date] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'