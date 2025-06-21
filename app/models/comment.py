from app.models import Base
from sqlalchemy.orm import relationship, Mapped, mapped_column 
from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Text 
from datetime import datetime, timezone 
from typing import List 

class Comment(Base):
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    text = Column(Text, nullable=False) 
    parent_comment_id = Column(Integer, ForeignKey("comments.id"), nullable=True, default=None) 
    depth: Mapped[int] = mapped_column(default=0)
    reply_count: Mapped[int] = mapped_column(default=0) 

    author = relationship("User", foreign_keys=[author_id], back_populates="comment_author")
    event = relationship("Event", foreign_keys=[event_id], back_populates="comment_event")
    
    replies: Mapped[List["Comment"]] = relationship(
    "Comment", 
    back_populates="parent_comment", 
    cascade="all, delete-orphan", 
    lazy="selectin" 
)
    
    parent_comment = relationship(
        "Comment", 
        back_populates="replies", 
        remote_side=[id] 
    )