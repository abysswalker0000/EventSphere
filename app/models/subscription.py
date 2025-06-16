from app.models import Base
from sqlalchemy.orm import relationship
from sqlalchemy import Column, Integer, ForeignKey, DateTime, UniqueConstraint, CheckConstraint
from datetime import datetime



class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index = True)
    created_at = Column(DateTime, default=datetime.utcnow)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    followee_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    follower = relationship("User", foreign_keys=[follower_id], back_populates="following_subscriptions")
    followee = relationship("User", foreign_keys=[followee_id], back_populates="follower_subscriptions")
    __table_args__ = (
        UniqueConstraint('follower_id', 'followee_id', name='uq_follower_followee'),
        CheckConstraint('follower_id != followee_id', name='cc_user_cannot_follow_self'),
    )