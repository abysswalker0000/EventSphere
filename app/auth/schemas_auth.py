from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

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

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    user_id: Optional[int] = None 

class UserCreateAuthSchema(BaseModel): 
    email: EmailStr
    password: str = Field(..., min_length=8)
    name: Optional[str] = Field(default=None, min_length=2, max_length=100) 

class UserLoginSchema(BaseModel):
    username: EmailStr 
    password: str

class UserWithTokenResponse(BaseModel):
    user: UserResponseSchema
    token: Token 