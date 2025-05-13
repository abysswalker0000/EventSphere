from pydantic import BaseModel
from datetime import datetime
from typing import Literal
from enum import Enum

class StatusVariation(str, Enum):
    going = "going"
    interested = "interested"
    not_going = "not going"

class ParticipationCreateSchema(BaseModel):
    user_id: int
    event_id: int
    status: Literal["going", "interested", "not going"] = "not going"

class ParticipationSchema(BaseModel):
    id: int
    user_id: int
    event_id: int
    joined_at: datetime
    status: Literal["going", "interested", "not going"]
