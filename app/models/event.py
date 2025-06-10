from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models import Base
from datetime import datetime
from app.models.user import User


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    description = Column(String, nullable=True)
    event_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    category_id = Column(Integer, ForeignKey("category.id"), nullable=False)

    author = relationship("User", back_populates="events")
    category = relationship("Category", back_populates="events")
    participants = relationship("Participation", back_populates="event")
    comment_event = relationship("Comment", back_populates="event")
    review_event = relationship("Review", back_populates="event")
    ticket_event = relationship("Ticket", back_populates="event")