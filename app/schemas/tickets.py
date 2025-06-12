from pydantic import BaseModel
from decimal import Decimal
from datetime import datetime
from typing import Optional

class TicketCreateSchema(BaseModel):
    user_id: int
    event_id: int
    price: Optional[Decimal] = None


class TicketUpdateSchema(BaseModel):
    price: Optional[Decimal] = None


class TicketResponseSchema(BaseModel):
    id: int
    user_id: int
    event_id: int
    price: Optional[Decimal]
    purchased_at: datetime