from pydantic import BaseModel, Field
from datetime import datetime
from typing_extensions import Annotated

class ReviewCreateSchemaAuthenticated(BaseModel):
    event_id: int
    comment: str
    rating: Annotated[int, Field(ge=1, le=5)]

class ReviewCreateSchemaWithoutBinding(BaseModel):
    event_id: int
    author_id: int
    comment: str
    rating: Annotated[int, Field(ge=1, le=5)]

class ReviewResponseSchema(BaseModel):
    id: int
    event_id: int
    author_id: int
    comment: str
    rating: Annotated[int, Field(ge=1, le=5)]
    created_at: datetime

class ReviewUpdateSchema(BaseModel):
    comment:str
    rating: Annotated[int, Field(ge=1, le=5)]