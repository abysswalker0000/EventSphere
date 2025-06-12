from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List, Optional 
import logging

from app.schemas.review import (
    ReviewCreateSchemaWithoutBinding,
    ReviewUpdateSchema,
    ReviewResponseSchema,
    ReviewCreateSchemaAuthenticated
)
from app.models.review import Review
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reviews",
    tags=["Reviews"]
)

@router.post(
    "/as_author",
    response_model=ReviewResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review specifying the author (temp for no-auth)"
)
async def create_review_as_author(
    review_data: ReviewCreateSchemaWithoutBinding,
    db: AsyncSession = Depends(get_db)
):
    db_review = Review(
        comment=review_data.comment,
        rating=review_data.rating,
        event_id=review_data.event_id,
        author_id=review_data.author_id
    )
    db.add(db_review)
    try:
        await db.commit()
        await db.refresh(db_review)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating review by author {review_data.author_id} for event {review_data.event_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create review. This user might have already reviewed this event, or event/user ID is invalid."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating review by author {review_data.author_id} for event {review_data.event_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the review."
        )
    return db_review

@router.get(
    "/user/{user_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews by a specific user"
)
async def get_reviews_by_user(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(
            select(Review).where(Review.author_id == user_id)
            .order_by(Review.created_at.desc())
            .offset(skip).limit(limit)
        )
        reviews = result.scalars().all()
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching reviews for user {user_id}."
        )

@router.get(
    "/event/{event_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews for a specific event"
)
async def get_reviews_by_event(
    event_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None
):
    query = select(Review).where(Review.event_id == event_id)
    if min_rating is not None:
        query = query.where(Review.rating >= min_rating)
    if max_rating is not None:
        query = query.where(Review.rating <= max_rating)
    
    query = query.order_by(Review.created_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(query)
        reviews = result.scalars().all()
        return reviews
    except Exception as e:
        logger.error(f"Error fetching reviews for event_id {event_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching reviews for event {event_id}."
        )

@router.get(
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Get a specific review by ID"
)
async def get_review_by_id(review_id: int, db: AsyncSession = Depends(get_db)):
    review: Review | None = None
    try:
        result = await db.execute(select(Review).filter(Review.id == review_id))
        review = result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching review with id {review_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching review {review_id}."
        )
    
    if not review:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Review with id {review_id} not found."
        )
    return review

@router.patch(
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Update a review"
)
async def update_review(
    review_id: int,
    review_update_data: ReviewUpdateSchema,
    db: AsyncSession = Depends(get_db)
):
    db_review: Review | None = None
    update_payload_str = review_update_data.model_dump_json(exclude_unset=True)
    try:
        result = await db.execute(select(Review).filter(Review.id == review_id))
        db_review = result.scalars().first()

        if not db_review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with id {review_id} not found to update."
            )
        
        updated_data = review_update_data.model_dump(exclude_unset=True)
        if not updated_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        for key, value in updated_data.items():
            setattr(db_review, key, value)
        
        await db.commit()
        await db.refresh(db_review)
        return db_review
        
    except HTTPException: 
        raise
    except Exception as e_general: 
        await db.rollback()
        review_info_for_log = f"event_id {db_review.event_id if db_review else 'N/A'}, author_id {db_review.author_id if db_review else 'N/A'}"
        logger.error(
            f"Unexpected error updating review id {review_id} ({review_info_for_log}) with payload {update_payload_str}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while updating review {review_id}."
        )

@router.delete(
    "/{review_id}",
    summary="Delete a review",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_review(review_id: int, db: AsyncSession = Depends(get_db)):
    db_review_to_delete: Review | None = None
    try:
        result = await db.execute(select(Review).filter(Review.id == review_id))
        db_review_to_delete = result.scalars().first()

        if not db_review_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with id {review_id} not found to delete."
            )

        await db.delete(db_review_to_delete)
        await db.commit()
        
        logger.info(f"Review (ID: {review_id}) by author_id {db_review_to_delete.author_id} for event_id {db_review_to_delete.event_id} deleted successfully.")
        return None

    except HTTPException:
        raise
    except Exception as e: 
        await db.rollback()
        review_info_for_log = f"author_id {db_review_to_delete.author_id if db_review_to_delete else 'N/A'}, event_id {db_review_to_delete.event_id if db_review_to_delete else 'N/A'}"
        logger.error(
            f"Error deleting review with id {review_id} ({review_info_for_log}): {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while deleting review {review_id}."
        )