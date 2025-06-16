from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List, Optional
import logging

from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreateSchema, UserResponseSchema, UserUpdateSchema
from app.auth import user_crud 
from app.auth.dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)

@router.post(
    "/",
    response_model=UserResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new user (Admin operation)",
    dependencies=[Depends(get_current_admin_user)]
)
async def create_user_by_admin_endpoint(
    user_data: UserCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    existing_user = await user_crud.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists."
        )
    try:
        db_user = await user_crud.create_user_by_admin(db=db, user_in=user_data)
        logger.info(f"Admin created user: {db_user.email}")
        return db_user
    except IntegrityError:
        await db.rollback()
        logger.warning(f"IntegrityError creating user by admin: {user_data.email} - Email already exists (race condition or other constraint).")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists or another integrity constraint was violated."
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error creating user by admin {user_data.email}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the user."
        )

@router.get(
    "/",
    response_model=List[UserResponseSchema],
    summary="Get all users (Admin operation)",
    dependencies=[Depends(get_current_admin_user)]
)
async def get_all_users_endpoint(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        users = await user_crud.get_users_paginated(db, skip=skip, limit=limit)
        return users
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching users."
        )

@router.get(
    "/me",
    response_model=UserResponseSchema,
    summary="Get current authenticated user's details"
)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.get(
    "/{user_id}",
    response_model=UserResponseSchema,
    summary="Get a specific user by ID (Admin or self)"
)
async def get_user_by_id_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to access details of user ID {user_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this user's details.")
    
    user: User | None = None
    try:
        user = await user_crud.get_user_by_id(db, user_id=user_id)
    except Exception as e:
        logger.error(f"Error fetching user with id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching user {user_id}."
        )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with id {user_id} not found."
        )
    return user

@router.patch(
    "/{user_id}",
    response_model=UserResponseSchema,
    summary="Update a user (Admin or self)"
)
async def update_user_endpoint(
    user_id: int,
    user_update_data: UserUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id != user_id and current_user.role != "admin":
        logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to update user ID {user_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this user.")
    if current_user.role != "admin":
        if user_update_data.role is not None and user_update_data.role != current_user.role : 
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Users cannot change their own role.")
        if user_update_data.is_active is not None and user_update_data.is_active != current_user.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Users cannot change their own active status.")
    
    if user_update_data.email and (current_user.id == user_id or current_user.role == "admin"):
        existing_email_user = await user_crud.get_user_by_email(db, email=user_update_data.email)
        if existing_email_user and existing_email_user.id != user_id:
             raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="This email is already registered by another user.")
    elif user_update_data.email and current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to change other user's email.")


    db_user: User | None = None
    update_payload_str = user_update_data.model_dump_json(exclude_unset=True)
    try:
        db_user = await user_crud.get_user_by_id(db, user_id=user_id)
        if not db_user: 
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found to update."
            )
        
        updated_user = await user_crud.update_existing_user(db=db, db_user=db_user, user_in=user_update_data)
        logger.info(f"User ID {user_id} (email: {updated_user.email}) updated by User ID {current_user.id}.")
        return updated_user
        
    except IntegrityError:
        await db.rollback()
        logger.warning(f"IntegrityError updating user id {user_id} with payload {update_payload_str}: Email may already exist.")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot update user: Email already exists or another integrity constraint was violated."
        )
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        user_email_for_log = db_user.email if db_user else "N/A"
        logger.error(
            f"Error updating user id {user_id} (email: {user_email_for_log}) with payload {update_payload_str}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while updating user {user_id}."
        )
    
@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a user (Admin operation)",
    dependencies=[Depends(get_current_admin_user)]
)
async def delete_user_endpoint(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user) 
):
    if current_admin.id == user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Administrator cannot delete their own account via this endpoint.")

    user_to_delete: User | None = None
    try:
        user_to_delete = await user_crud.get_user_by_id(db, user_id=user_id)
        if not user_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"User with id {user_id} not found to delete."
            )
        
        user_email_for_log = user_to_delete.email
        await user_crud.delete_existing_user(db=db, db_user=user_to_delete)
        logger.info(f"User {user_email_for_log} (ID: {user_id}) deleted by admin ID {current_admin.id}.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except IntegrityError as e_integrity:
        await db.rollback()
        user_email_for_log = user_to_delete.email if user_to_delete else "N/A"
        logger.error(
            f"IntegrityError deleting user id {user_id} (email: {user_email_for_log}): {str(e_integrity)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot delete user {user_id} as they are referenced by other entities that prevent deletion."
        )
    except Exception as e:
        await db.rollback()
        user_email_for_log = user_to_delete.email if user_to_delete else "N/A"
        logger.error(
            f"Error deleting user with id {user_id} (email: {user_email_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting user {user_id}."
        )