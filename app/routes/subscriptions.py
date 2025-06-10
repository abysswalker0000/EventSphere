from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.schemas.subscription import SubscriptionCreateSchema, SubscriptionResponseSchema
from app.models.subscription import Subscription
from typing import List
from app.database import get_db
from sqlalchemy import select

router = APIRouter()

@router.get("/",tags=["Subscriptions"], summary="Get all Subscriptions", response_model=List[SubscriptionResponseSchema])
async def get_subscriptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription))
    subscriptions = result.scalars().all()
    return subscriptions

@router.post("/", tags=["Subscriptions"], summary="Create new Subscription")
async def create_subscription(new_subscription: SubscriptionCreateSchema, db:AsyncSession = Depends(get_db)):
    db_subscription = Subscription(follower_id = new_subscription.follower_id, followee_id = new_subscription.followee_id)
    db.add(db_subscription)
    await db.commit()
    await db.refresh(db_subscription)
    return {"success": True, "message": "Subscription created successfully"}