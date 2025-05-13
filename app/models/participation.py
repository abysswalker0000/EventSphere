from app.models import Base
from sqlalchemy.orm import relationship
from datetime import datetime
from sqlalchemy import Column, Integer, Enum, DateTime, ForeignKey, UniqueConstraint
import enum


class Status_Variation(enum.Enum):
    going = "going"
    interested = "interested"
    not_going = "not going"


class Participation(Base):
    __tablename__ = "participations"
    id = Column(Integer, primary_key=True, index=True)  
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    joined_at = Column(DateTime, default=datetime.utcnow)
    status = Column(Enum(Status_Variation), nullable=False, default=Status_Variation.not_going)

    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="unique_user_event"),
    )

    user = relationship("User", back_populates="participations")
    event = relationship("Event", back_populates="participants")