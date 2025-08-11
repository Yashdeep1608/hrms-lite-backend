import enum
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base

class LoanRepaymentType(str, enum.Enum):
    DAILY = "daily"          # fixed amount every day
    WEEKLY = "weekly"        # fixed amount every week
    MONTHLY = "monthly"      # fixed amount every month
    BULLET = "bullet"        # full payment at the end
    FLEXIBLE = "flexible"    # pay any amount at any time
    NO_COST= "no_cost"       # no cost to repay the loan

class LoanStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    DEFAULTED = "defaulted"

class LoanRepaymentStatus (str, enum.Enum):
    PENDING = "pending"
    PAID = "paid"
    OVERDUE = "overdue"

class Loan(Base):
    __tablename__ = "loans"

    id = Column(Integer, primary_key=True, index=True)

    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False, index=True)
    lender_name = Column(String(255), nullable=False)  # name of person/company giving the loan
    lender_contact = Column(String(1000), nullable=True)

    principal_amount = Column(Numeric(12, 2), nullable=False)  # amount borrowed
    interest_rate = Column(Numeric(5, 2), nullable=True)       # percentage (optional for flat repayment)
    total_amount_payable = Column(Numeric(12, 2), nullable=False)  # principal + interest total

    repayment_type = Column(Enum(LoanRepaymentType), nullable=False)
    repayment_amount = Column(Numeric(12, 2), nullable=True)  # fixed amount for each period (if applicable)
    repayment_day = Column(Integer, nullable=True)    # 1=Monday .. 7=Sunday (for weekly loans) and 1 to 31 for monthly loans
    emi_number = Column(Integer, nullable = True)

    start_date = Column(Date, nullable=False) # when the loan started
    end_date = Column(Date, nullable=True) # when the loan ends (if applicable)

    notes = Column(String, nullable=True)

    status = Column(Enum(LoanStatus), default=LoanStatus.ACTIVE)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    repayments = relationship(
        "LoanRepayment",
        back_populates="loan",
        cascade="all, delete-orphan"
    )

class LoanRepayment(Base):
    __tablename__ = "loan_repayments"

    id = Column(Integer, primary_key=True, index=True)
    loan_id = Column(Integer, ForeignKey("loans.id", ondelete="CASCADE"), nullable=False, index=True)
    
    payment_date = Column(Date, nullable=False)
    amount_paid = Column(Numeric(12, 2), nullable=False)
    notes = Column(String, nullable=True)
    status = Column(Enum(LoanRepaymentStatus), default=LoanRepaymentStatus.PENDING)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    loan = relationship("Loan", back_populates="repayments")
