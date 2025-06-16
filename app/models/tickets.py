from sqlalchemy import Column, Integer, UniqueConstraint, DateTime,DECIMAL, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    price = Column(DECIMAL, nullable=True)
    purchased_at = Column(DateTime, default=datetime.utcnow)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)

    visitor = relationship("User", foreign_keys=[user_id], back_populates="visitor")
    event = relationship("Event", foreign_keys=[event_id], back_populates="ticket_event")
    __table_args__ = (
        UniqueConstraint("user_id", "event_id", name="uq_user_event_ticket"),
    )