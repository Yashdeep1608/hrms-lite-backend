import enum
from sqlalchemy import Boolean, Column, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.db.base import Base
from app.models.enums import OrderPaymentMethod

class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True)
    business_id = Column(Integer, ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    isd_code = Column(String(10),nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(String(1000), nullable=True)
    gst_number = Column(String(50), nullable=True)
    pan_number = Column(String(50), nullable=True)
    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    purchases = relationship("SupplierPurchase", back_populates="supplier", cascade="all, delete-orphan")
    transactions = relationship("SupplierTransaction", back_populates="supplier", cascade="all, delete-orphan")


class SupplierPurchase(Base):
    __tablename__ = "supplier_purchases"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    purchase_number = Column(String(255), nullable=False)
    supplier_invoice_number = Column(String(255), nullable=True)  # from supplier
    file_url = Column(String(1000), nullable=True)  # scanned PDF/image
    purchase_date = Column(Date, nullable=False)

    taxable_amount = Column(Numeric(10, 2), default=0)  # before tax
    tax_rate = Column(Numeric(10, 2), default=0)
    total_tax_amount = Column(Numeric(10, 2), default=0) # CGST+SGST+IGST combined
    total_amount = Column(Numeric(10, 2),default=0)     # final invoice amount

    notes = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    supplier = relationship("Supplier", back_populates="purchases")
    items = relationship("SupplierPurchaseItem", back_populates="purchase", cascade="all, delete-orphan")

class SupplierPurchaseItem(Base):
    __tablename__ = "supplier_purchase_items"

    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("supplier_purchases.id", ondelete="CASCADE"), nullable=False)
    product_id = Column(Integer,nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=False)

    tax_rate = Column(Numeric(5, 2), nullable=True)     # e.g., 18.00
    tax_amount = Column(Numeric(10, 2), nullable=True)  # total tax value for this item
    total_amount = Column(Numeric(10, 2), nullable=False)  # price incl. tax

    purchase = relationship("SupplierPurchase", back_populates="items")

class SupplierTransaction(Base):
    __tablename__ = "supplier_transactions"

    id = Column(Integer, primary_key=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id", ondelete="CASCADE"), nullable=False)
    purchase_id = Column(Integer, ForeignKey("supplier_purchases.id", ondelete="SET NULL"), nullable=True)  # link if purchase
    transaction_id = Column(String,nullable=False,unique=True)
    transaction_date = Column(Date, nullable=False)
    
    transaction_type = Column(Enum("purchase", "payment", name="supplier_transaction_type"), nullable=False)
    payment_method = Column(Enum(OrderPaymentMethod), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)

    notes = Column(String, nullable=True)

    supplier = relationship("Supplier", back_populates="transactions")
    purchase = relationship("SupplierPurchase")
