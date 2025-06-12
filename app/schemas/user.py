from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserCreateSchema(BaseModel):
    email: EmailStr
    bio: Optional[str] = Field(None, max_length=1000)

class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    bio: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    bio: Optional[str] = Field(None, max_length=1000)