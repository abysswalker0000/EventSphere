from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List, Optional
import logging

from app.database import get_db
from app.models.review import Review
from app.models.user import User
from app.models.event import Event
from app.schemas.review import (
    ReviewCreateSchema, 
    ReviewCreateSchemaWithoutBinding,
    ReviewUpdateSchema,
    ReviewResponseSchema
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/reviews", 
    tags=["Reviews"]
)


@router.post(
    "/", 
    response_model=ReviewResponseSchema, 
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review for an event (Authenticated user)"
)
async def create_review(
    review_data: ReviewCreateSchema, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    
    event_check = await db.get(Event, review_data.event_id)
    if not event_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Event with id {review_data.event_id} not found.")
    existing_review_q = await db.execute(
    select(Review).where(Review.author_id == current_user.id, Review.event_id == review_data.event_id)
    )
    if existing_review_q.scalars().first():
        raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="You have already submitted a review for this event.")

    db_review = Review(
        comment=review_data.comment,
        rating=review_data.rating,
        event_id=review_data.event_id,
        author_id=current_user.id 
    )
    db.add(db_review)
    try:
        await db.commit()
        await db.refresh(db_review)
        logger.info(f"Review created by user ID {current_user.id} for event ID {review_data.event_id}")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating review by user ID {current_user.id} for event ID {review_data.event_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create review. You might have already reviewed this event, or the event ID is invalid."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating review by user ID {current_user.id} for event ID {review_data.event_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the review."
        )
    return db_review

@router.post(
    "/as_author_admin",
    response_model=ReviewResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new review specifying the author (Admin only)",
    dependencies=[Depends(get_current_admin_user)]
)
async def create_review_as_author_by_admin( 
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
        logger.info(f"Review created via /as_author_admin: author_id={review_data.author_id}, event_id={review_data.event_id}")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError (admin) creating review with data {review_data.model_dump()}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create review due to a data conflict."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error (admin) creating review with data {review_data.model_dump()}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )
    return db_review

@router.get(
    "/event/{event_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews for a specific event (Public)"
)
async def get_reviews_for_event_public( 
    event_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    min_rating: Optional[int] = None,
    max_rating: Optional[int] = None
):
    query = select(Review).where(Review.event_id == event_id)
    if min_rating is not None and 1 <= min_rating <= 5:
        query = query.where(Review.rating >= min_rating)
    if max_rating is not None and 1 <= max_rating <= 5:
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
    "/user/{user_id}",
    response_model=List[ReviewResponseSchema],
    summary="Get all reviews by a specific user (Public)"
)
async def get_reviews_by_user_public( 
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
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Get a specific review by ID (Public)"
)
async def get_review_by_id_public(
    review_id: int, 
    db: AsyncSession = Depends(get_db)
):
    review: Review | None = None
    try:
        result = await db.execute(select(Review).filter(Review.id == review_id))
        review = result.scalars().first()
        if not review:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with id {review_id} not found."
            )
        return review
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching review with id {review_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching review {review_id}."
        )

@router.patch(
    "/{review_id}",
    response_model=ReviewResponseSchema,
    summary="Update a review (Author only)"
)
async def update_own_review( 
    review_id: int,
    review_update_data: ReviewUpdateSchema,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
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
        
        if db_review.author_id != current_user.id:
            logger.warning(f"User ID {current_user.id} attempted to update review ID {review_id} owned by user ID {db_review.author_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this review."
            )
        
        updated_data = review_update_data.model_dump(exclude_unset=True)
        if not updated_data:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields provided for update."
            )

        for key, value in updated_data.items():
            if value is not None:
                setattr(db_review, key, value)
        
        await db.commit()
        await db.refresh(db_review)
        logger.info(f"Review ID {review_id} updated by author ID {current_user.id}.")
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
    summary="Delete a review (Author or Admin only)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_own_or_admin_review( 
    review_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_review_to_delete: Review | None = None
    try:
        result = await db.execute(select(Review).filter(Review.id == review_id))
        db_review_to_delete = result.scalars().first()

        if not db_review_to_delete:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Review with id {review_id} not found to delete."
            )

        is_author = db_review_to_delete.author_id == current_user.id
        is_admin = current_user.role == "admin"

        if not (is_author or is_admin):
            logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to delete review ID {review_id} owned by user ID {db_review_to_delete.author_id}.")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this review."
            )
        
        review_info_for_log = f"ID {review_id}, author_id {db_review_to_delete.author_id}, event_id {db_review_to_delete.event_id}"
        await db.delete(db_review_to_delete)
        await db.commit()
        
        deleted_by_role = "admin" if is_admin and not is_author else "author"
        logger.info(f"Review ({review_info_for_log}) deleted successfully by {deleted_by_role} (current_user ID: {current_user.id}).")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

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