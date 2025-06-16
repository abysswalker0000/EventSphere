from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select
from typing import List, Optional
import logging

from app.database import get_db
from app.models.subscription import Subscription
from app.models.user import User 
from app.schemas.subscription import (
    SubscriptionCreateExplicitSchema, 
    SubscriptionCreateByUserSchema,  
    SubscriptionResponseSchema
)
from app.auth.dependencies import get_current_active_user, get_current_admin_user

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/subscriptions",
    tags=["Subscriptions"]
)


@router.post(
    "/user/{followee_id}/subscribe", 
    response_model=SubscriptionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a user (Authenticated user)"
)
async def subscribe_to_user(
    followee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if current_user.id == followee_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User cannot subscribe to themselves."
        )
    followee_user = await db.get(User, followee_id)
    if not followee_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {followee_id} (to follow) not found.")
    existing_subscription_q = await db.execute(select(Subscription).where(Subscription.follower_id == current_user.id, Subscription.followee_id == followee_id))
    if existing_subscription_q.scalars().first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="You are already subscribed to this user.")

    db_subscription = Subscription(
        follower_id=current_user.id,
        followee_id=followee_id
    )
    db.add(db_subscription)
    try:
        await db.commit()
        await db.refresh(db_subscription)
        logger.info(f"User ID {current_user.id} subscribed to user ID {followee_id}.")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError creating subscription: follower_id={current_user.id}, followee_id={followee_id}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create subscription. You might already be subscribed or user ID is invalid."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error creating subscription: follower_id={current_user.id}, followee_id={followee_id}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while creating the subscription."
        )
    return db_subscription

@router.delete(
    "/user/{followee_id}/unsubscribe", 
    summary="Unsubscribe from a user (Authenticated user)",
    status_code=status.HTTP_204_NO_CONTENT
)
async def unsubscribe_from_user(
    followee_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    db_subscription: Subscription | None = None
    try:
        query = select(Subscription).where(
            Subscription.follower_id == current_user.id,
            Subscription.followee_id == followee_id
        )
        result = await db.execute(query)
        db_subscription = result.scalars().first()

        if not db_subscription:
            logger.info(f"User ID {current_user.id} attempted to unsubscribe from user ID {followee_id}, but was not subscribed.")
            return Response(status_code=status.HTTP_204_NO_CONTENT)

        subscription_id_for_log = db_subscription.id
        await db.delete(db_subscription)
        await db.commit()
        
        logger.info(f"User ID {current_user.id} unsubscribed from user ID {followee_id} (Subscription ID: {subscription_id_for_log}).")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException: 
        raise
    except Exception as e:
        await db.rollback()
        logger.error(
            f"Error unsubscribing user ID {current_user.id} from user ID {followee_id}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while unsubscribing."
        )
@router.post(
    "/admin_set_subscription",
    response_model=SubscriptionResponseSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new subscription (Admin only, explicit IDs)",
    dependencies=[Depends(get_current_admin_user)]
)
async def create_subscription_by_admin(
    subscription_data: SubscriptionCreateExplicitSchema,
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
        logger.info(f"Admin created subscription: follower_id={subscription_data.follower_id}, followee_id={subscription_data.followee_id}.")
    except IntegrityError as e_integrity:
        await db.rollback()
        logger.warning(
            f"IntegrityError (admin) creating subscription: {subscription_data.model_dump()}: {str(e_integrity)}"
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Subscription already exists or user/followee ID is invalid."
        )
    except Exception as e_general:
        await db.rollback()
        logger.error(
            f"Unexpected error (admin) creating subscription: {subscription_data.model_dump()}: {str(e_general)}",
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred."
        )
    return db_subscription

@router.get(
    "/",
    response_model=List[SubscriptionResponseSchema],
    summary="Get all subscription records (Admin only, paginated)",
    dependencies=[Depends(get_current_admin_user)]
)
async def get_all_subscriptions_admin( 
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    try:
        result = await db.execute(select(Subscription).offset(skip).limit(limit).order_by(Subscription.created_at.desc()))
        subscriptions = result.scalars().all()
        return subscriptions
    except Exception as e:
        logger.error(f"Error fetching all subscriptions (admin): {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching subscription records."
        )

@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponseSchema,
    summary="Get a specific subscription record by ID (Admin or participants)"
)
async def get_subscription_by_id_restricted( 
    subscription_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user) 
):
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
    
    is_participant = current_user.id == subscription.follower_id or current_user.id == subscription.followee_id
    is_admin = current_user.role == "admin"
    if not (is_participant or is_admin):
        logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to access subscription ID {subscription_id} not belonging to them.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this subscription.")
        
    return subscription


@router.delete(
    "/{subscription_id}/admin", 
    summary="Delete a subscription by its ID (Admin only)",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(get_current_admin_user)]
)
async def delete_subscription_by_id_admin(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    db_subscription: Subscription | None = None
    try:
        result = await db.execute(select(Subscription).filter(Subscription.id == subscription_id))
        db_subscription = result.scalars().first()

        if not db_subscription:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Subscription with id {subscription_id} not found."
            )

        sub_info_for_log = f"ID: {db_subscription.id}, follower: {db_subscription.follower_id}, followee: {db_subscription.followee_id}"
        await db.delete(db_subscription)
        await db.commit()
        
        logger.info(f"Subscription ({sub_info_for_log}) deleted by admin.")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        sub_info_for_log = f"follower: {db_subscription.follower_id if db_subscription else 'N/A'}, followee: {db_subscription.followee_id if db_subscription else 'N/A'}"
        logger.error(
            f"Error deleting subscription with id {subscription_id} ({sub_info_for_log}) by admin: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the subscription."
        )

@router.get(
    "/followers_of/{user_id}",
    response_model=List[SubscriptionResponseSchema], 
    summary="Get all followers of a specific user (Public)"
)
async def get_user_followers_public(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    
    user_check = await db.get(User, user_id)
    if not user_check:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"User with id {user_id} not found.")
        
    query = select(Subscription).where(Subscription.followee_id == user_id)
    query = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(query)
        subscriptions_or_users = result.scalars().all()
        return subscriptions_or_users
    except Exception as e:
        logger.error(f"Error fetching followers for user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching followers for user {user_id}."
        )

@router.get(
    "/following_by/{user_id}",
    response_model=List[SubscriptionResponseSchema], 
    summary="Get all users a specific user is following (Owner or Admin)"
)
async def get_user_following_restricted(
    user_id: int, 
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user), 
    skip: int = 0,
    limit: int = 100
):
    if current_user.id != user_id and current_user.role != "admin":
        logger.warning(f"User ID {current_user.id} (role: {current_user.role}) attempted to access following list of user ID {user_id}.")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to access this information.")

    query = select(Subscription).where(Subscription.follower_id == user_id)
    query = query.order_by(Subscription.created_at.desc()).offset(skip).limit(limit)
    try:
        result = await db.execute(query)
        subscriptions_or_users = result.scalars().all()
        return subscriptions_or_users
    except Exception as e:
        logger.error(f"Error fetching users followed by user_id {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while fetching users followed by user {user_id}."
        )