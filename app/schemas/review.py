from pydantic import BaseModel, Field
from datetime import datetime
from typing_extensions import Annotated
from typing import Optional

class ReviewCreateSchema(BaseModel):
    event_id: int 
    comment: str = Field(..., min_length=1, max_length=2000)
    rating: Annotated[int, Field(..., ge=1, le=5)]

class ReviewCreateSchemaWithoutBinding(BaseModel):
    event_id: int
    author_id: int
    comment: str = Field(..., min_length=1, max_length=2000)
    rating: Annotated[int, Field(..., ge=1, le=5)]

class ReviewUpdateSchema(BaseModel):
    comment: Optional[str] = Field(default=None, min_length=1, max_length=2000) 
    rating: Optional[Annotated[int, Field(ge=1, le=5)]] = None 

class ReviewResponseSchema(BaseModel):
    id: int
    event_id: int
    author_id: int 
    comment: str
    rating: int
    created_at: datetime

    class Config:
        from_attributes = True