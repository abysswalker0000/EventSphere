from pydantic import BaseModel, Field
from decimal import Decimal
from datetime import datetime
from typing import Optional


class TicketPurchaseSchema(BaseModel):
    quantity: Optional[int] = Field(default=1, ge=1) 
    pass 

class TicketCreateAdminSchema(BaseModel):
    user_id: int
    event_id: int
    price: Decimal = Field(..., ge=0)

class TicketUpdateAdminSchema(BaseModel):
    price: Optional[Decimal] = Field(default=None, ge=0)

class TicketResponseSchema(BaseModel):
    id: int
    user_id: int    
    event_id: int  
    price: Decimal
    purchased_at: datetime

    class Config:
        from_attributes = True