from pydantic import BaseModel, Field
from datetime import datetime
from decimal import Decimal

class TicketCreateSchema(BaseModel):
    user_id: int
    event_id: int
    price: Decimal | None

class TicketBaseSchema(BaseModel):
    price: Decimal 
    user_id: int
    event_id: int

class TicketResponseSchema(TicketBaseSchema):
    id: int
    purchased_at: datetime