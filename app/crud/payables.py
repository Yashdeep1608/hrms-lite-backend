from typing import Optional

from sqlalchemy import and_, or_
from app.models.enums import RoleTypeEnum
from app.models.expense import Expense, ExpenseCategory
from sqlalchemy.orm import Session
from app.models.user import User
from app.schemas.expense import *

def create_expense(db: Session, payload: AddEditExpense,current_user:User):
    expense = Expense(
        business_id=current_user.business_id,
        created_by_user_id =current_user.id,
        category_id=payload.category_id,
        expense_date=payload.expense_date,
        amount =payload.amount,
        notes = payload.notes,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense

def update_expense(db: Session, expense_id: int, payload: AddEditExpense):
    expense = db.query(Expense).filter(Expense.id == expense_id).first()
    expense.category_id = payload.category_id
    expense.expense_date = payload.expense_date
    expense.amount = payload.amount
    expense.notes = payload.notes
    db.commit()
    db.refresh(expense)
    return expense

def get_expense_by_id(db: Session, expense_id: int):
    return db.query(Expense).filter(Expense.id == expense_id).first()

def get_expenses(db: Session,filters:ExpenseFilters,current_user:User):
    query = db.query(Expense)

    if filters.category_id:
        query = query.filter(Expense.category_id == filters.category_id)
    if filters.search:
        query = query.filter(or_(Expense.notes.like(f"%{filters.search}%"),))
    if filters.from_date:
        query = query.filter(Expense.expense_date >= filters.from_date)
    if filters.to_date:
        query = query.filter(Expense.expense_date <= filters.to_date)
    if current_user.role not in  [RoleTypeEnum.ADMIN,RoleTypeEnum.SUPERADMIN,RoleTypeEnum.PLATFORM_ADMIN]:
        query = query.filter(Expense.created_by_user_id == current_user.id)
    
    total = query.count()
    sort_attr = getattr(Expense, filters.sort_by or "created_at", None)
    if sort_attr is not None:
        query = query.order_by(sort_attr.asc() if filters.sort_dir == "asc" else sort_attr.desc())

    # Count and paginate
    skip = (filters.page - 1) * filters.page_size
    items = query.offset(skip).limit(filters.page_size).all()
    # Pagination
    return {
        "items":items,
        "total":total
    }

def delete_expense(db: Session, expense_id: int):
    expense = db.get(Expense,expense_id)
    if not expense: 
        raise Exception("Expense not found")
    db.delete(expense)
    db.commit()

def get_expense_categories(db:Session):
    return db.query(ExpenseCategory).all()