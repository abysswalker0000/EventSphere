from pydantic import BaseModel
from datetime import datetime

class SubscriptionCreateExplicitSchema(BaseModel): 
    follower_id: int
    followee_id: int

class SubscriptionCreateByUserSchema(BaseModel):
    pass 

class SubscriptionResponseSchema(BaseModel):
    id: int
    follower_id: int 
    followee_id: int 
    created_at: datetime

    class Config:
        from_attributes = True