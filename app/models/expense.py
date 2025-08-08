from sqlalchemy import Boolean, Column, Date, DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey('businesses.id', ondelete='CASCADE'), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey('expense_categories.id', ondelete='CASCADE'), nullable=False, index=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    amount = Column(Numeric(10, 2), default=0)
    notes = Column(String, nullable=True)
    expense_date = Column(Date, nullable=False)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    business = relationship("Business", back_populates="expenses")
    category = relationship("ExpenseCategory", back_populates="expenses")
    created_by_user = relationship("User")

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey('expense_categories.id'), nullable=True)  # self-referential
    is_active = Column(Boolean, default=True)
    image_url = Column(String(1000), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    expenses = relationship("Expense", back_populates="category")
    subcategories = relationship("ExpenseCategory", backref="parent", remote_side=[id])