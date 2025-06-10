from app.models import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, ForeignKey, DateTime,String
from datetime import datetime

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index = True)
    created_at = Column(DateTime, default=datetime.utcnow)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(String(1000), nullable=False)

    author = relationship("User", foreign_keys=[author_id], back_populates="comment_author")
    event = relationship("Event", foreign_keys=[event_id], back_populates="comment_event")
