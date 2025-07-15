from sqlalchemy import Column, Integer, String, CHAR
from app.db.base import Base

class Country(Base):
    __tablename__ = 'countries'

    id = Column(Integer, primary_key=True, index=True)
    code = Column(CHAR(2), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(Integer, nullable=False)
    currency_symbol = Column(String(10))
    currency = Column(String(3))
    continent = Column(String(30))
    continent_code = Column(CHAR(2))
