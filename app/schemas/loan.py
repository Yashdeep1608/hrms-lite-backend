from datetime import date
from typing import Optional
from pydantic import BaseModel

class AddEditLoan(BaseModel):
    lender_name:Optional[str] = None
    lender_contact:Optional[str] = None
    repayment_type:Optional[str] = None
    repayment_day:Optional[int] = None
    emi_number:Optional[int] = None
    repayment_amount:Optional[float] = None
    principal_amount:Optional[float] = None
    interest_rate:Optional[float] = None
    total_amount_payable:Optional[float] = None

    start_date:Optional[date] =  None
    end_date:Optional[date] = None

    notes:Optional[str] = None

class LoanRepaymentRequest(BaseModel):
    loan_id: int
    repayment_id:Optional[int] = None
    payment_date:Optional[date] = None
    payment_amount:Optional[float] = None
    notes:Optional[str] = None

class LoanFilters(BaseModel):
    search:Optional[str] = None
    status :Optional[str] = None
    from_date: Optional[date] = None
    to_date: Optional[date] = None
    page:int
    page_size:int
    sort_by:str = 'created_at'
    sort_dir:str = 'desc'
