from pydantic import BaseModel
from datetime import datetime

class EventSchema(BaseModel):
    title: str
    author_id: int
    event_time: datetime
    category_id: int