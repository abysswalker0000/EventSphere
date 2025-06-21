from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError 
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Optional
import logging

from app.database import get_db
from app.models.comment import Comment
from app.models.user import User 
from app.models.event import Event
from app.schemas.comment import (
    CommentCreateSchema, 
    CommentCreateSchemaWithoutBinding,
    CommentUpdateSchema,
    CommentResponseSchema
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
)

@router.post(
    "/", 
    response_model=CommentResponseSchema, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new comment or a reply (Authenticated user)"
)
async def create_comment_or_reply(
    comment_data: CommentCreateSchema, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    event_check = await db.get(Event, comment_data.event_id)
    if not event_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {comment_data.event_id} not found.")

    parent_comment_obj: Optional[Comment] = None
    depth = 0
    if comment_data.parent_comment_id:
        parent_comment_obj = await db.get(Comment, comment_data.parent_comment_id)
        if not parent_comment_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent comment with id {comment_data.parent_comment_id} not found.")
        if parent_comment_obj.event_id != comment_data.event_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reply must be to a comment within the same event.")
        if parent_comment_obj.depth >= 4: 
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum reply depth reached.")
        depth = parent_comment_obj.depth + 1

    db_comment = Comment(
        text=comment_data.text,
        event_id=comment_data.event_id,
        author_id=current_user.id,
        parent_comment_id=comment_data.parent_comment_id,
        depth=depth
    )
    db.add(db_comment)
    
    if parent_comment_obj:
        parent_comment_obj.reply_count += 1
        db.add(parent_comment_obj)

    try:
        await db.commit()
        await db.refresh(db_comment)
        query_options = [selectinload(Comment.author)]
        if db_comment.parent_comment_id:
            query_options.append(selectinload(Comment.parent_comment).selectinload(Comment.author))
        
        refreshed_comment_result = await db.execute(
            select(Comment).options(*query_options).filter(Comment.id == db_comment.id)
        )
        db_comment = refreshed_comment_result.scalars().unique().first()

        logger.info(f"Comment/Reply ID {db_comment.id} created by user ID {current_user.id} for event ID {comment_data.event_id}, parent: {comment_data.parent_comment_id}")
    except IntegrityError as e_integrity: 
        await db.rollback()
        logger.warning(
            f"IntegrityError creating comment/reply by user ID {current_user.id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, 
            detail="Could not create comment/reply due to a data conflict."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating comment/reply by user ID {current_user.id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )
    return db_comment

@router.post(
    "/as_author_admin", 
    response_model=CommentResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new comment or reply specifying the author (Admin only)",
    dependencies=[Depends(get_current_admin_user)]
)
async def create_comment_or_reply_as_author_by_admin(
    new_comment_data: CommentCreateSchemaWithoutBinding,
    db: AsyncSession = Depends(get_db)
):
    event_check = await db.get(Event, new_comment_data.event_id)
    if not event_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {new_comment_data.event_id} not found.")
    
    parent_comment_obj: Optional[Comment] = None
    depth = 0
    if new_comment_data.parent_comment_id:
        parent_comment_obj = await db.get(Comment, new_comment_data.parent_comment_id)
        if not parent_comment_obj:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Parent comment with id {new_comment_data.parent_comment_id} not found.")
        if parent_comment_obj.event_id != new_comment_data.event_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reply must be to a comment within the same event.")
        if parent_comment_obj.depth >= 4:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum reply depth reached.")
        depth = parent_comment_obj.depth + 1

    db_comment = Comment(
        text=new_comment_data.text,
        event_id=new_comment_data.event_id,
        author_id=new_comment_data.author_id,
        parent_comment_id=new_comment_data.parent_comment_id,
        depth=depth
    )
    db.add(db_comment)

    if parent_comment_obj:
        parent_comment_obj.reply_count += 1
        db.add(parent_comment_obj)

    try:
        await db.commit()
        await db.refresh(db_comment)
        query_options = [selectinload(Comment.author)]
        if db_comment.parent_comment_id:
            query_options.append(selectinload(Comment.parent_comment).selectinload(Comment.author))
        
        refreshed_comment_result = await db.execute(
            select(Comment).options(*query_options).filter(Comment.id == db_comment.id)
        )
        db_comment = refreshed_comment_result.scalars().unique().first()
        logger.info(f"Admin created Comment/Reply: author_id={new_comment_data.author_id}, event_id={new_comment_data.event_id}, parent: {new_comment_data.parent_comment_id}")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError (admin) creating comment/reply with data {new_comment_data.model_dump()}: {str(e_integrity)}"
        )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Could not create comment/reply due to a data conflict.")
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error (admin) creating comment/reply with data {new_comment_data.model_dump()}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred.")
    return db_comment


@router.get(
    "/event/{event_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all top-level comments with replies for a specific event"
)
async def get_event_comments_with_replies(
    event_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0, 
    limit: int = 20 
):
    try:
        load_options = [
            selectinload(Comment.author), 
            selectinload(Comment.replies).selectinload(Comment.author), 
            selectinload(Comment.replies).selectinload(Comment.replies).selectinload(Comment.author), 
        ]
        stmt = (
            select(Comment)
            .where(Comment.event_id == event_id)
            .where(Comment.parent_comment_id.is_(None)) 
            .options(*load_options)
            .order_by(Comment.created_at.desc()) 
            .offset(skip)
            .limit(limit)
        )
        result = await db.execute(stmt)
        comments = result.scalars().unique().all() 
        return comments
    except Exception as e:
        logger.error(f"Error fetching comments for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred while fetching comments for event {event_id}.")


@router.get(
    "/user/{user_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all comments and replies by a specific user"
)
async def get_all_comments_and_replies_by_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        load_options = [
            selectinload(Comment.author), 
            selectinload(Comment.replies).selectinload(Comment.author), 
            selectinload(Comment.replies).selectinload(Comment.replies).selectinload(Comment.author) 
        ]

        query = (
            select(Comment)
            .where(Comment.author_id == user_id)
            .options(*load_options) 
            .order_by(Comment.created_at.desc())
            .offset(skip).limit(limit)
        )
        result = await db.execute(query)
        comments = result.scalars().unique().all()
        return comments
    except Exception as e:
        logger.error(f"Error fetching comments for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred while fetching comments for user {user_id}.")
    
@router.get(
    "/{comment_id}",
    response_model=CommentResponseSchema, 
    summary="Get a specific comment by ID with all its replies"
)
async def get_comment_with_replies_by_id(
    comment_id: int, 
    db: AsyncSession = Depends(get_db)
):
    comment: Comment | None = None
    try:
        query = (
            select(Comment)
            .options(
                selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.author),
                selectinload(Comment.replies).selectinload(Comment.replies).selectinload(Comment.author)
            )
            .filter(Comment.id == comment_id)
        )
        result = await db.execute(query)
        comment = result.scalars().unique().first()
        
        if not comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comment with id {comment_id} not found.")
        return comment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching comment with replies for id {comment_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An error occurred while fetching comment {comment_id}.")

@router.patch(
    "/{comment_id}",
    response_model=CommentResponseSchema,
    summary="Update a comment (Author only)"
)
async def update_own_comment(
    comment_id: int,
    comment_update_data: CommentUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_comment: Comment | None = None
    update_payload_str = comment_update_data.model_dump_json(exclude_unset=True)
    try:
        query = select(Comment).options(selectinload(Comment.author), selectinload(Comment.replies)).filter(Comment.id == comment_id)
        result = await db.execute(query)
        db_comment = result.scalars().unique().first()

        if not db_comment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Comment with id {comment_id} not found to update.")
        if db_comment.author_id != current_user.id:
            logger.warning(f"User ID {current_user.id} attempted to update comment ID {comment_id} owned by user ID {db_comment.author_id}.")
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this comment.")
        
        updated_data = comment_update_data.model_dump(exclude_unset=True)
        if not updated_data or not updated_data.get("text"):
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No text provided for update or empty update.")

        db_comment.text = updated_data["text"]
        await db.commit()
        await db.refresh(db_comment)
        await db.refresh(db_comment, attribute_names=['author', 'replies', 'parent_comment'])
        
        logger.info(f"Comment ID {comment_id} updated by author ID {current_user.id}.")
        return db_comment
    except HTTPException:
        raise
    except Exception as e_general:
        await db.rollback()
        comment_author_for_log = db_comment.author_id if db_comment else "N/A"
        logger.error(
            f"Unexpected error updating comment id {comment_id} (author_id: {comment_author_for_log}) with payload {update_payload_str}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred while updating comment {comment_id}.")

@router.delete(
    "/{comment_id}",
    summary="Delete a comment (Author or Admin only)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_own_or_admin_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_comment_to_delete: Comment | None = None
    parent_comment_id_to_update: int | None = None
    
    try:
        result = await db.execute(select(Comment).filter(Comment.id == comment_id))
        db_comment_to_delete = result.scalars().first()

        if not db_comment_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Comment with id {comment_id} not found to delete."
            )

        is_author = db_comment_to_delete.author_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_author or is_admin):
            logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to delete comment ID {comment_id} owned by user ID {db_comment_to_delete.author_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this comment."
            )
        
        parent_comment_id_to_update = db_comment_to_delete.parent_comment_id
        comment_info_for_log = f"ID {comment_id}, author_id {db_comment_to_delete.author_id}, event_id {db_comment_to_delete.event_id}"
        
        await db.delete(db_comment_to_delete)
        if parent_comment_id_to_update:
            parent_comment = await db.get(Comment, parent_comment_id_to_update)
            if parent_comment:
                parent_comment.reply_count = max(0, parent_comment.reply_count - 1)
                db.add(parent_comment)
        
        await db.commit()
        
        deleted_by_role = "admin" if is_admin and not is_author else "author"
        logger.info(f"Comment ({comment_info_for_log}) and its replies (if any, due to cascade) deleted successfully by {deleted_by_role} (current_user ID: {current_user.id}).")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        author_id_for_log = "N/A"
        if db_comment_to_delete:
            author_id_for_log = str(db_comment_to_delete.author_id)
        
        logger.error(
            f"Error deleting comment with id {comment_id} (author_id: {author_id_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting comment {comment_id}."
        )