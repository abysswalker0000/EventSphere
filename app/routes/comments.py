from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.comment import CommentCreateSchemaAuthenticated, CommentCreateSchemaWithoutBinding,CommentResponseSchema
from app.models.comment import Comment
from typing import List
from app.database import get_db
from sqlalchemy import select


router = APIRouter(
    tags=["Comments"]
)

# @router.post(
#     "/",
#     summary="Create a new comment (authenticated user style)" НУЖЕН ТОКЕН ПОЛЬЗОВАТЕЛЯ + ФУНКЦИЯ !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
# )

@router.post(
    "/as_author",
    summary="Create a new comment specifying the author"
)
async def create_comment_as_author_user_style(
    new_comment: CommentCreateSchemaWithoutBinding,
    db: AsyncSession = Depends(get_db)
):
    db_comment = Comment(
        text=new_comment.text,
        event_id=new_comment.event_id,
        author_id=new_comment.author_id
    )
    db.add(db_comment)
    await db.commit()
    await db.refresh(db_comment)
    return {"success": True, "message": "Comment added successfully by specified author", "comment_id": db_comment.id}

@router.get(
    "/user/{user_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all comments by a specific user"
)
async def get_comments_by_user_user_style(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment).where(Comment.author_id == user_id).order_by(Comment.created_at.desc())
    )
    comments = result.scalars().all()
    return comments

@router.get(
    "/event/{event_id}",
    response_model=List[CommentResponseSchema],
    summary="Get all comments for a specific event"
)
async def get_comments_by_event_user_style(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Comment).where(Comment.event_id == event_id).order_by(Comment.created_at.desc())
    )
    comments = result.scalars().all()
    return comments
