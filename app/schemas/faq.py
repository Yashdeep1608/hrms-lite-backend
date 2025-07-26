from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FAQBaseSchema(BaseModel):
    business_id: int
    question: Optional[str] = Field(..., example="Your working hours?")
    answer: Optional[str] = Field(..., example="9am to 5pm.")

class FAQCreateSchema(FAQBaseSchema):
    pass

class FAQUpdateSchema(BaseModel):
    question: Optional[str] = Field(..., example="Your working hours?")
    answer: Optional[str] = Field(..., example="9am to 5pm.")
    is_active: Optional[bool] = None

