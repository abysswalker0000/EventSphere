from fastapi import APIRouter
from app.schemas.user import UserSchema

router = APIRouter()

users = []

@router.post("/", tags=["Users"], summary="Add new users")
def add_user(user: UserSchema):
    users.append(user)
    return {"ok": True, "message": "User added successfully"}

@router.get("/", tags=["Users"], summary="Get all users")
def get_users():
    return users