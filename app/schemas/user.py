from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class UserBaseSchema(BaseModel):
    email: EmailStr
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = True
    role: Optional[str] = Field(default="user", pattern="^(user|organizer|admin)$")

class UserMinimalResponseSchema(BaseModel): 
    id: int
    name: str
    class Config:
        from_attributes = True

class UserCreateSchema(UserBaseSchema):
    password: str = Field(..., min_length=8)
    

class UserUpdateAdminSchema(BaseModel):
    email: Optional[EmailStr] = None
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = None
    role: Optional[str] = Field(default=None, pattern="^(user|organizer|admin)$")

class UserProfileUpdateSchema(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    bio: Optional[str] = Field(default=None, max_length=1000)

class UserPasswordUpdateSchema(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
    new_password_confirm: str 

    @validator('new_password_confirm')
    def passwords_match(cls, v, values, **kwargs):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Новые пароли не совпадают')
        return v

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