from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    bio = Column(String(1000), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    events = relationship("Event", back_populates="author")
    participations = relationship("Participation", back_populates="user")
    following_subscriptions = relationship("Subscription",foreign_keys="Subscription.follower_id", back_populates="follower" )
    follower_subscriptions = relationship("Subscription",foreign_keys="Subscription.followee_id", back_populates="followee" )
    comment_author = relationship("Comment", back_populates="author")
    reviewer = relationship("Review", back_populates="reviewer")
    visitor = relationship("Ticket", back_populates="visitor")
    