from app.models import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, ForeignKey, DateTime,String
from datetime import datetime

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer,primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment = Column(String(1000), nullable=False)
    rating = Column(Integer, nullable=False)

    reviewer = relationship("User", foreign_keys=[author_id], back_populates="reviewer")
    event = relationship("Event", foreign_keys=[event_id], back_populates="review_event")
