from pydantic import BaseModel,Field

class CategorySchema(BaseModel):
    name: str

class CategoryUpdateSchema(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)

class CategoryResponseSchema(BaseModel):
    id: int
    name: str