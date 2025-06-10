from pydantic import BaseModel
from datetime import datetime


class SubscriptionCreateSchema(BaseModel):
    follower_id: int
    followee_id: int


class SubscriptionResponseSchema(BaseModel):
    id: int
    follower_id: int
    followee_id: int
    created_at: datetime