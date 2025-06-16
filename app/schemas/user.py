from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBaseSchema(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = True
    role: Optional[str] = Field(default="user", pattern="^(user|organizer|admin)$")

class UserCreateSchema(UserBaseSchema):
    password: str = Field(..., min_length=8)

class UserUpdateSchema(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(default=None, pattern="^(user|organizer|admin)$")

class UserResponseSchema(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    role: str
    created_at: datetime

    class Config:
        from_attributes = True