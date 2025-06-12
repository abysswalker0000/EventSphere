from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, func, delete as sqlalchemy_delete
from typing import List, Optional
import logging

from app.schemas.subscription import (
    SubscriptionCreateSchema,
    SubscriptionResponseSchema
)
from app.models.subscription import Subscription
from app.models.user import User 
from app.database import get_db

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)

@router.post(
    "/",
    response_model=SubscriptionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subscription"
)
async def create_subscription(
    subscription_data: SubscriptionCreateSchema,
    db: AsyncSession = Depends(get_db)
):
    if subscription_data.follower_id == subscription_data.followee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User cannot subscribe to themselves."
        )
    db_subscription = Subscription(
        follower_id=subscription_data.follower_id,
        followee_id=subscription_data.followee_id
    )
    db.add(db_subscription)
    try:
        await db.commit()
        await db.refresh(db_subscription)
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating subscription: follower_id={subscription_data.follower_id}, followee_id={subscription_data.followee_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subscription already exists or user/followee ID is invalid."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating subscription: follower_id={subscription_data.follower_id}, followee_id={subscription_data.followee_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the subscription."
        )
    return db_subscription

@router.get(
    "/",
    response_model=List[SubscriptionResponseSchema],
    summary="Get all subscription records (admin, paginated)"
)
async def get_all_subscriptions(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(select(Subscription).offset(skip).limit(limit).order_by(Subscription.created_at.desc()))
        subscriptions = result.scalars().all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error fetching all subscriptions: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching subscription records."
        )

@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponseSchema,
    summary="Get a specific subscription record by ID"
)
async def get_subscription_by_id(subscription_id: int, db: AsyncSession = Depends(get_db)):
    subscription: Subscription | None = None
    try:
        result = await db.execute(select(Subscription).filter(Subscription.id == subscription_id))
        subscription = result.scalars().first()
    except Exception as e:
        logger.error(f"Error fetching subscription with id {subscription_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching subscription record {subscription_id}."
        )
    
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Subscription record with id {subscription_id} not found."
        )
    return subscription

@router.delete(
    "/follower/{follower_id}/followee/{followee_id}",
    summary="Delete a subscription by follower and followee IDs",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_subscription_by_user_ids(
    follower_id: int,
    followee_id: int,
    db: AsyncSession = Depends(get_db)
):
    db_subscription: Subscription | None = None
    try:
        query = select(Subscription).where(
            Subscription.follower_id == follower_id,
            Subscription.followee_id == followee_id
        )
        result = await db.execute(query)
        db_subscription = result.scalars().first()

        if not db_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription from follower {follower_id} to followee {followee_id} not found."
            )

        await db.delete(db_subscription)
        await db.commit()
        
        logger.info(f"Subscription (ID: {db_subscription.id}) from follower {follower_id} to followee {followee_id} deleted successfully.")
        return None

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error deleting subscription from follower {follower_id} to followee {followee_id}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the subscription."
        )

@router.get(
    "/followers_of/{user_id}",
    response_model=List[SubscriptionResponseSchema], 
    summary="Get all followers of a specific user"
)
async def get_user_followers(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    query = select(Subscription).where(Subscription.followee_id == user_id) 
    query = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(query)
        subscriptions = result.scalars().all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error fetching followers for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching followers for user {user_id}."
        )

@router.get(
    "/following_by/{user_id}",
    response_model=List[SubscriptionResponseSchema], 
    summary="Get all users a specific user is following"
)
async def get_user_following(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    query = select(Subscription).where(Subscription.follower_id == user_id)
    query = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(query)
        subscriptions = result.scalars().all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error fetching users followed by user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users followed by user {user_id}."
        )