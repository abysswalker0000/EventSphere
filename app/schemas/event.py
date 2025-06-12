from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional 


class EventBaseSchema(BaseModel):
    title: str = Field(..., min_length=3, max_length=255) 
    description: Optional[str] = Field(default=None, max_length=5000) 
    event_date: datetime 
    category_id: int

class EventCreateSchema(EventBaseSchema):
    author_id: int 

class EventUpdateSchema(BaseModel):
    title: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[str] = Field(default=None, max_length=5000)
    event_date: Optional[datetime] = None
    category_id: Optional[int] = None

class EventResponseSchema(EventBaseSchema):
    id: int
    author_id: int 
    created_at: datetime

