from pydantic import BaseModel
from datetime import datetime

class CommentCreateSchemaWithoutBinding(BaseModel):
    author_id: int
    text: str
    event_id: int

class CommentCreateSchemaAuthenticated(BaseModel):
    text: str
    event_id: int

class CommentUpdateSchema(BaseModel):
    text:str


class CommentResponseSchema(BaseModel):
    id: int
    text: str
    created_at: datetime
    author_id: int
    event_id: int