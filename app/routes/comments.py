from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List
import logging

from app.schemas.comment import (
    CommentCreateSchemaWithoutBinding,
    CommentUpdateSchema,
    CommentResponseSchema
)
from app.models.comment import Comment
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/comments",
    tags=["Comments"]
)

@router.post(
    "/as_author",
    summary="Create a new comment specifying the author (temp for no-auth)",
    response_model=CommentResponseSchema,
    status_code=status.HTTP_201_CREATED
)
async def create_comment_as_author(
    new_comment_data: CommentCreateSchemaWithoutBinding,
    db: AsyncSession = Depends(get_db)
):
    db_comment = Comment(
        text=new_comment_data.text,
        event_id=new_comment_data.event_id,
        author_id=new_comment_data.author_id
    )
    db.add(db_comment)
    try:
        await db.commit()
        await db.refresh(db_comment)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating comment with data {new_comment_data.model_dump()}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create comment due to a data conflict."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating comment with data {new_comment_data.model_dump()}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the comment."
        )
    return db_comment

@router.get(
    "/user/{user_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all comments by a specific user"
)
async def get_comments_by_user(user_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Comment).where(Comment.author_id == user_id).order_by(Comment.created_at.desc())
        )
        comments = result.scalars().all()
        return comments
    except Exception as e:
        logger.error(f"Error fetching comments for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching comments for user {user_id}."
        )

@router.get(
    "/event/{event_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all comments for a specific event"
)
async def get_comments_by_event(event_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(
            select(Comment).where(Comment.event_id == event_id).order_by(Comment.created_at.desc())
        )
        comments = result.scalars().all()
        return comments
    except Exception as e:
        logger.error(f"Error fetching comments for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching comments for event {event_id}."
        )

@router.get(
    "/{comment_id}",
    response_model=CommentResponseSchema,
    summary="Get a specific comment by ID"
)
async def get_comment_by_id(comment_id: int, db: AsyncSession = Depends(get_db)):
    comment: Comment | None = None
    try:
        result = await db.execute(select(Comment).filter(Comment.id == comment_id))
        comment = result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching comment with id {comment_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching comment {comment_id}."
        )
    
    if not comment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comment with id {comment_id} not found."
        )
    return comment

@router.patch(
    "/{comment_id}",
    response_model=CommentResponseSchema,
    summary="Update a comment"
)
async def update_comment(
    comment_id: int,
    comment_update_data: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    db_comment: Comment | None = None
    update_payload_str = comment_update_data.model_dump_json(exclude_unset=True)
    try:
        result = await db.execute(select(Comment).filter(Comment.id == comment_id))
        db_comment = result.scalars().first()

        if not db_comment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {comment_id} not found to update."
            )
        
        updated_data = comment_update_data.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        for key, value in updated_data.items():
            setattr(db_comment, key, value)
        
        await db.commit()
        await db.refresh(db_comment)
        return db_comment
        
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError updating comment id {comment_id} with payload {update_payload_str}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not update comment due to a data conflict."
        )
    except HTTPException:
        raise
    except Exception as e_general:
        await db.rollback()
        comment_text_for_log = db_comment.text[:50] + "..." if db_comment and db_comment.text else "N/A"
        logger.error(
            f"Unexpected error updating comment id {comment_id} (text_start: {comment_text_for_log}) with payload {update_payload_str}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while updating comment {comment_id}."
        )

@router.delete(
    "/{comment_id}",
    summary="Delete a comment",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_comment(comment_id: int, db: AsyncSession = Depends(get_db)):
    db_comment_to_delete: Comment | None = None
    try:
        result = await db.execute(select(Comment).filter(Comment.id == comment_id))
        db_comment_to_delete = result.scalars().first()

        if not db_comment_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {comment_id} not found to delete."
            )

        await db.delete(db_comment_to_delete)
        await db.commit()
        
        logger.info(f"Comment (ID: {comment_id}, text_start: {db_comment_to_delete.text[:50] + '...'}) deleted successfully.")
        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        comment_text_for_log = db_comment_to_delete.text[:50] + "..." if db_comment_to_delete and db_comment_to_delete.text else "N/A"
        logger.error(
            f"Error deleting comment with id {comment_id} (text_start: {comment_text_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting comment {comment_id}."
        )