from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional

from app.models.user import User
from app.schemas.user import UserCreateSchema, UserUpdateAdminSchema, UserProfileUpdateSchema
from app.auth.schemas_auth import UserCreateAuthSchema 
from app.auth.security import get_password_hash

async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    user = await db.get(User, user_id)
    return user

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).filter(User.email == email))
    return result.scalars().first()

async def get_users_paginated(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[User]:
    result = await db.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    return result.scalars().all()

async def create_user_by_admin(db: AsyncSession, user_in: UserCreateSchema) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        bio=user_in.bio,
        hashed_password=hashed_password,
        is_active=user_in.is_active if user_in.is_active is not None else True,
        role=user_in.role if user_in.role else "user"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def register_new_user(db: AsyncSession, user_in: UserCreateAuthSchema) -> User:
    hashed_password = get_password_hash(user_in.password)
    db_user = User(
        email=user_in.email,
        name=user_in.name,
        hashed_password=hashed_password,
        bio=None,
        is_active=True,
        role="user"
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_existing_user(db: AsyncSession, db_user: User, user_in: UserUpdateAdminSchema) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def delete_existing_user(db: AsyncSession, db_user: User) -> None:
    await db.delete(db_user)
    await db.commit()
    return None

async def update_user_profile(db: AsyncSession, db_user: User, user_in: UserProfileUpdateSchema) -> User:
    update_data = user_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_user, key, value)
    await db.commit()
    await db.refresh(db_user)
    return db_user

async def update_user_password(db: AsyncSession, db_user: User, new_password: str) -> User:
    db_user.hashed_password = get_password_hash(new_password)
    await db.commit()
    await db.refresh(db_user) 
    return db_user