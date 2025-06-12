from pydantic import BaseModel
from datetime import datetime
from enum import Enum

class StatusVariation(str, Enum):
    going = "going"
    interested = "interested"
    not_going = "not going"

class ParticipationCreateExplicitSchema(BaseModel):
    user_id: int
    event_id: int
    status: StatusVariation = StatusVariation.interested

class ParticipationSetStatusSchema(BaseModel):
    status: StatusVariation

class ParticipationResponseSchema(BaseModel):
    id: int
    user_id: int
    event_id: int
    joined_at: datetime
    status: StatusVariation

    class Config:
        from_attributes = True

class ParticipationWithUserInfoResponseSchema(BaseModel):
    id: int
    user_id: int 
    event_id: int 
    joined_at: datetime
    status: StatusVariation

    class Config:
        from_attributes = True

class ParticipationWithEventInfoResponseSchema(BaseModel):
    id: int
    user_id: int
    event_id: int 
    joined_at: datetime
    status: StatusVariation

    class Config:
        from_attributes = True