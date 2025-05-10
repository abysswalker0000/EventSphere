from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.user import UserSchema
from app.models.user import User
from app.database import get_db
from sqlalchemy import select

router = APIRouter()

@router.post("/", tags=["Users"], summary="Add new user")
async def add_user(user: UserSchema, db: AsyncSession = Depends(get_db)):
    db_user = User(email=user.email, bio=user.bio)
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return {"ok": True, "message": "User added successfully"}

@router.get("/", tags=["Users"], summary="Get all users")
async def get_users(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User))
    users = result.scalars().all()
    return users