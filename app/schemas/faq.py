from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class FAQTranslationSchema(BaseModel):
    language: str = Field(..., example="en")
    question: str = Field(..., example="Your working hours?")
    answer: str = Field(..., example="9am to 5pm.")

class FAQBaseSchema(BaseModel):
    business_id: int
    translations: List[FAQTranslationSchema]

class FAQCreateSchema(FAQBaseSchema):
    pass

class FAQUpdateSchema(BaseModel):
    translations: Optional[List[FAQTranslationSchema]] = None
    is_active: Optional[bool] = None

