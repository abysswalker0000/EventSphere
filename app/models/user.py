from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    bio = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    role = Column(String(50), default="user", nullable=False) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    events = relationship("Event", back_populates="author")
    participations = relationship("Participation", back_populates="user", cascade="all, delete-orphan")
    
    following_subscriptions = relationship(
        "Subscription",
        foreign_keys="Subscription.follower_id",
        back_populates="follower",
        cascade="all, delete-orphan"
    )
    follower_subscriptions = relationship(
        "Subscription",
        foreign_keys="Subscription.followee_id",
        back_populates="followee",
        cascade="all, delete-orphan"
    )
    
    comment_author = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    reviewer = relationship("Review", back_populates="reviewer", cascade="all, delete-orphan")
    visitor = relationship("Ticket", back_populates="visitor", cascade="all, delete-orphan")