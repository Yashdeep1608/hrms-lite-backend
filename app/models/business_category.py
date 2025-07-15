from sqlalchemy import Column, Integer, String
from app.db.base import Base

class BusinessCategory(Base):
    __tablename__ = 'business_categories'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(String)

