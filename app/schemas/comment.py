from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List
from app.schemas.user import UserMinimalResponseSchema

class CommentBaseSchema(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)

class CommentCreateSchema(CommentBaseSchema):
    event_id: int 
    parent_comment_id: Optional[int] = None 

class CommentCreateSchemaWithoutBinding(CommentBaseSchema):
    author_id: int
    event_id: int
    parent_comment_id: Optional[int] = None

class CommentUpdateSchema(BaseModel):
    text: Optional[str] = Field(default=None, min_length=1, max_length=5000)

class CommentResponseSchema(CommentBaseSchema):
    id: int
    created_at: datetime
    author_id: int 
    author: Optional[UserMinimalResponseSchema] = None
    event_id: int  
    parent_comment_id: Optional[int] = None
    reply_count: int
    replies: List["CommentResponseSchema"] = Field(default_factory=list)

    class Config:
        from_attributes = True
