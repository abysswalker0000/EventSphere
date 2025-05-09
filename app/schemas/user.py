from pydantic import BaseModel, EmailStr, Field

class UserSchema(BaseModel):
    email: EmailStr
    bio: str | None = Field(max_length=1000)

class UserAgeSchema(UserSchema):
    age: int = Field(ge=12, le=120)