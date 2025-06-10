from fastapi import APIRouter, Depends, HTTPException 
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.review import ( 
    ReviewCreateSchemaAuthenticated,
    ReviewCreateSchemaWithoutBinding,
    ReviewResponseSchema
)
from app.models.review import Review 
from app.models.user import User    
from app.database import get_db
from sqlalchemy import select
from typing import List

router = APIRouter(
    tags=["Reviews"] 
)

@router.post(
    "/as_author",
    summary="Create a new review specifying the author"
)
async def create_review_as_author_user_style(
    new_review: ReviewCreateSchemaWithoutBinding,
    db: AsyncSession = Depends(get_db)
):
    db_review = Review(
        comment=new_review.comment,
        rating=new_review.rating,     
        event_id=new_review.event_id,
        author_id=new_review.author_id
    )
    db.add(db_review)
    await db.commit()
    await db.refresh(db_review)
    return {"success": True, "message": "Review added successfully by specified author", "review_id": db_review.id}
@router.get(
    "/user/{user_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews by a specific user"
)
async def get_reviews_by_user_user_style(user_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review).where(Review.author_id == user_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return reviews

@router.get(
    "/event/{event_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews for a specific event"
)
async def get_reviews_by_event_user_style(event_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Review).where(Review.event_id == event_id).order_by(Review.created_at.desc())
    )
    reviews = result.scalars().all()
    return reviews