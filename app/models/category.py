from datetime import datetime, timezone
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean, Column, DateTime, Integer, ForeignKey,String
from app.db.base import Base

class Category(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    parent_id = Column(Integer, ForeignKey('categories.id'), nullable=True)
    business_id = Column(Integer,ForeignKey('businesses.id'),nullable = False)
    is_active = Column(Boolean, default=True)
    category_image = Column(String(1000), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    businesses = relationship("Business", back_populates="categories")
    products = relationship("Product", foreign_keys='Product.category_id',back_populates="product_category")
    services = relationship("Service", foreign_keys='Service.category_id',back_populates="service_category")
