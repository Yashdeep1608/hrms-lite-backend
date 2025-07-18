from typing import Optional

from sqlalchemy import and_
from app.models.faq import FAQ
from sqlalchemy.orm import Session
from app.schemas.faq import *

def create_faq(db: Session, faq_in: FAQCreateSchema):
    faq = FAQ(
        business_id=faq_in.business_id,
        content={"translations": [t.model_dump() for t in faq_in.translations]}
    )
    db.add(faq)
    db.commit()
    db.refresh(faq)
    return faq

def update_faq(db: Session, faq_id: int, faq_in: FAQUpdateSchema):
    faq = db.query(FAQ).filter(FAQ.id == faq_id).first()
    if not faq:
        raise Exception("FAQ not found")
    if faq_in.translations is not None:
        faq.content["translations"] = [t.model_dump() for t in faq_in.translations]
    if faq_in.is_active is not None:
        faq.is_active = faq_in.is_active
    db.commit()
    db.refresh(faq)
    return faq

def get_faq_by_id(db: Session, faq_id: int):
    return db.query(FAQ).filter(FAQ.id == faq_id).first()

def get_faqs(db: Session, business_id: Optional[int] = None):
    query = db.query(FAQ)
    if business_id:
        query = query.filter_by(business_id=business_id)
    return query.all()

def delete_faq(db: Session, faq_id: int):
    faq = db.query(FAQ).filter_by(id=faq_id).first()
    if not faq: 
        raise Exception("faq_not_found")
    db.delete(faq)
    db.commit()