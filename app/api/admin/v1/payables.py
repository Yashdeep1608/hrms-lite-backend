from fastapi import APIRouter, Depends, Request
from app.core.dependencies import get_current_user
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from app.helpers.response import ResponseHandler
from app.crud import payables as crud_payable
from app.db.session import get_db
from app.helpers.translator import Translator
from app.helpers.utils import get_lang_from_request
from app.schemas.expense import *
from app.schemas.loan import *
from app.schemas.supplier import *

router = APIRouter(
    prefix="/api/admin/v1/payables",
    tags=["Payables"],
    dependencies=[Depends(get_current_user)]
)
translator = Translator()

# Expenses APIs
@router.post("/create-expense")
def create_expense(payload: AddEditExpense, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.create_expense(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/update-expense/{expense_id}")
def update_expense(expense_id: int, payload: AddEditExpense, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.update_expense(db, expense_id, payload)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-expenses")
def get_expenses(filters:ExpenseFilters, request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_expenses(db, filters, current_user)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/get-expense/{expense_id}")
def get_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_expense_by_id(db, expense_id)
        return ResponseHandler.success(message=translator.t("success", lang), data=data)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/delete-expense/{expense_id}")
def delete_expense(expense_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.delete_expense(db, expense_id)
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/get-expense-categories")
def get_expense_categories(request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_expense_categories(db)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

# Loans APIs
@router.post("/create-loan")
def create_loan(payload: AddEditLoan, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.create_loan(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/update-loan/{loan_id}")
def update_loan(loan_id: int, payload: AddEditLoan, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.update_expense(db, loan_id, payload)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-loans")
def get_loans(filters:LoanFilters, request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_loans(db, filters, current_user)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/get-loan/{loan_id}")
def get_loan(loan_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_loan_by_id(db, loan_id)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/delete-loan/{loan_id}")
def delete_loan(loan_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.delete_loan(db, loan_id)
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/add-loan-repayment")
def add_load_repayment(payload:LoanRepaymentRequest, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.add_loan_repayment(db, payload)
        return ResponseHandler.success(message=translator.t("paid_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )


# Suppliers APIs
@router.post("/create-supplier")
def create_supplier(payload: AddEditSupplier, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.cerate_supplier(db, payload, current_user)
        return ResponseHandler.success(message=translator.t("created_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.put("/update-supplier/{supplier_id}")
def update_supplier(supplier_id: int, payload: AddEditSupplier, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.update_supplier(db, supplier_id, payload)
        return ResponseHandler.success(message=translator.t("updated_successfully", lang), data=data.id)
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-suppliers")
def get_suppliers(filters:SupplierFilters, request: Request, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_suppliers(db, filters, current_user)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.delete("/delete-supplier/{supplier_id}")
def delete_supplier(supplier_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.delete_supplier(db, supplier_id)
        return ResponseHandler.success(message=translator.t("deleted_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/add-supplier-purchase")
def add_supplier_purchase(payload:AddSupplierPurchase, request: Request, db: Session = Depends(get_db),current_user=Depends(get_current_user)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.add_supplier_purchase(db, payload,current_user)
        return ResponseHandler.success(message=translator.t("paid_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("added_successfully", lang),
            error=str(e)
        )

@router.post("/add-transactions")
def add_transactions(transactions:List[TransactionRequest], request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        crud_payable.add_transactions(db, transactions)
        return ResponseHandler.success(message=translator.t("added_successfully", lang))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.get("/get-supplier_summary/{supplier_id}")
def get_supplier_summary(supplier_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_supplier_summary(db, supplier_id)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.get("/get-purchase/{purchase_id}")
def get_supplier_purchase_detail(purchase_id: int, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_supplier_purchase_detail(db, purchase_id)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )

@router.post("/get-supplier-purchases")
def get_supplier_purchases(filters:SupplierPurchaseFilters, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_supplier_purchases(db, filters)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
    
@router.post("/get-supplier-transactions")
def get_supplier_transactions(filters:SupplierTransactionFilters, request: Request, db: Session = Depends(get_db)):
    lang = get_lang_from_request(request)
    try:
        data = crud_payable.get_supplier_transactions(db, filters)
        return ResponseHandler.success(message=translator.t("success", lang), data=jsonable_encoder(data))
    except Exception as e:
        return ResponseHandler.internal_error(
            message=translator.t("something_went_wrong", lang),
            error=str(e)
        )
