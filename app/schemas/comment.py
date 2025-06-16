from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class CommentCreateSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000)
    event_id: int 

class CommentCreateSchemaWithoutBinding(BaseModel):
    author_id: int
    text: str = Field(..., min_length=1, max_length=1000)
    event_id: int

class CommentUpdateSchema(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=1000)

class CommentResponseSchema(BaseModel):
    id: int
    text: str
    created_at: datetime
    author_id: int 
    event_id: int  

    class Config:
        from_attributes = True