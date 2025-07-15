from sqlalchemy import Column, Integer, String, CHAR
from app.db.base import Base

class State(Base):
    __tablename__ = 'states'

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(CHAR(2), nullable=False)
    country_code = Column(CHAR(2), nullable=False)
