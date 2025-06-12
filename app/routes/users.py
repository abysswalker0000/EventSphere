from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from typing import List
import logging

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreateSchema, UserResponseSchema, UserUpdateSchema

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post(
    "/",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_user(
    new_user: UserCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    db_user = User(email=new_user.email, bio=new_user.bio)
    db.add(db_user)
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"User created: {db_user.email}")
        return db_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )

@router.get(
    "/",
    response_model=List[UserResponseSchema]
)
async def get_users(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(User).offset(skip).limit(limit).order_by(User.created_at.desc())
        )
        users = result.scalars().all()
        return users
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching users."
        )

@router.get(
    "/{user_id}",
    response_model=UserResponseSchema
)
async def get_user_by_id(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )
    return user

@router.patch(
    "/{user_id}",
    response_model=UserResponseSchema
)
async def update_user(
    user_id: int,
    user_update: UserUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    db_user = result.scalars().first()
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )
    updated_data = user_update.model_dump(exclude_unset=True)
    for key, value in updated_data.items():
        setattr(db_user, key, value)
    try:
        await db.commit()
        await db.refresh(db_user)
        logger.info(f"User updated: {db_user.email}")
        return db_user
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists."
        )

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(User).filter(User.id == user_id))
    user_to_delete = result.scalars().first()
    if not user_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )
    await db.delete(user_to_delete)
    await db.commit()
    logger.info(f"User deleted: {user_to_delete.email}")
    return None