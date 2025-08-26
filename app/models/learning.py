from sqlalchemy import Column, DateTime, Integer, String, Text
from datetime import datetime, timezone
from app.db.base import Base
from sqlalchemy.dialects.postgresql import JSONB

class VideoTutorial(Base):
    __tablename__ = "video_tutorials"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    link = Column(String) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class HowToGuide(Base):
    __tablename__ = "how_to_guides"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    image_url = Column(String)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class LatestUpdate(Base):
    __tablename__ = "latest_updates"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))