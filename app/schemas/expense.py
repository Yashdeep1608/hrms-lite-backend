from datetime import date
from typing import Optional
from pydantic import BaseModel

class AddEditExpense(BaseModel):
    category_id:Optional[int] = None,
    amount:Optional[float] = 0.00,
    notes:Optional[str] = None,
    expense_date:Optional[date] = None,

class ExpenseFilters(BaseModel):
    search:Optional[str] = None
    category_id:Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'

